"""API integration checks, each running against a fresh temporary SQLite database."""
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import timedelta
from fastapi.testclient import TestClient
from backend.app import create_app, now
from backend.import_words import import_csv


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.app=create_app(Path(self.tmp.name)/'test.sqlite3')
        self.client=TestClient(self.app)
        self.client.__enter__()
        self.me=self.client.get('/api/me').json()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.tmp.cleanup()

    def words(self,**params):
        response=self.client.get('/api/words',params=params)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def review(self,wid,rating='good',event='test-event-001'):
        return self.client.post('/api/review',json={'word_id':wid,'rating':rating,'event_id':event})

    def test_seed_search_pagination(self):
        topics=self.client.get('/api/topics').json()
        self.assertEqual(len(topics),30)
        self.assertTrue(all(t['word_count']==15 for t in topics))
        self.assertEqual(self.words()['total'],450)
        self.assertTrue(self.words(q='hungry')['items'])
        self.assertTrue(self.words(q='đói')['items'])
        self.assertEqual(self.words(q="' OR 1=1 --")['total'],0)
        self.assertEqual(self.words(q='%')['total'],0)
        self.assertNotEqual(self.words(page=1)['items'][0]['id'],self.words(page=2)['items'][0]['id'])
        self.assertEqual(self.client.get('/api/words?page=0').status_code,422)

    def test_bookmark_not_learning(self):
        wid=self.words()['items'][0]['id']
        self.assertEqual(self.client.put(f'/api/words/{wid}/bookmark',json={'saved':True}).status_code,200)
        self.assertEqual(self.words(status='saved')['total'],1)
        self.assertEqual(self.words(status='new')['total'],450)
        self.assertEqual(self.client.get('/api/stats').json()['learned'],0)
        self.assertEqual(self.client.put('/api/words/99999/bookmark',json={'saved':True}).status_code,404)

    def test_review_schedule_idempotency(self):
        wid=self.words()['items'][0]['id']
        first=self.review(wid)
        self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json()['interval_days'],1)
        self.assertEqual(self.review(wid).json()['repetitions'],1)
        self.assertEqual(self.review(wid,'easy').status_code,409)
        self.assertEqual(self.review(wid,'easy','test-event-002').json()['interval_days'],3)
        self.assertEqual(self.review(wid,'easy','test-event-003').json()['interval_days'],9)
        stats=self.client.get('/api/stats').json()
        for key,value in [('learned',1),('mastered',1),('today_words',1),('today_reviews',3),('streak',1)]:
            self.assertEqual(stats[key],value)
        self.assertEqual(self.review(wid,'again','test-event-004').json()['repetitions'],0)
        self.assertEqual(self.client.get('/api/review?mode=due').json(),[])
        with self.app.state.db.connect() as conn:
            conn.execute('UPDATE progress SET due_at=?',((now()-timedelta(minutes=1)).isoformat(),))
        self.assertEqual(len(self.client.get('/api/review?mode=due').json()),1)

    def test_quiz_server_grading_and_retry(self):
        response=self.client.post('/api/quiz',json={'count':5,'topic_id':1})
        self.assertEqual(response.status_code,200,response.text)
        session=response.json();q=session['questions'][0]
        self.assertEqual(len(session['questions']),5)
        self.assertNotIn('word_id',q)
        lookup={w['term']:w['id'] for w in self.words(topic_id=1)['items']}
        endpoint=f"/api/quiz/{session['id']}/answer"
        self.assertEqual(self.client.post(endpoint,json={'position':0,'option_id':99999}).status_code,422)
        response=self.client.post(endpoint,json={'position':0,'option_id':lookup[q['prompt']]})
        self.assertTrue(response.json()['correct'])
        self.assertEqual(self.client.post(endpoint,json={'position':0,'option_id':lookup[q['prompt']]}).json(),response.json())
        stats=self.client.get('/api/stats').json()
        self.assertEqual(stats['quiz_answers'],1)
        self.assertEqual(stats['accuracy'],100)
        self.assertEqual(stats['today_reviews'],1)
        q=session['questions'][1]
        wrong=next(o['id'] for o in q['options'] if o['id']!=lookup[q['prompt']])
        self.assertFalse(self.client.post(endpoint,json={'position':1,'option_id':wrong}).json()['correct'])
        self.assertEqual(self.client.get('/api/stats').json()['accuracy'],50)

    def test_typing_normalization_and_expiry(self):
        session=self.client.post('/api/quiz',json={'mode':'typing','count':5,'topic_id':1}).json()
        q=session['questions'][0]
        self.assertEqual(q['options'],[])
        words={w['meaning']:w['term'] for w in self.words(topic_id=1)['items']}
        endpoint=f"/api/quiz/{session['id']}/answer"
        response=self.client.post(endpoint,json={'position':0,'text':'  '+words[q['prompt']].upper()+'  '})
        self.assertTrue(response.json()['correct'])
        with self.app.state.db.connect() as conn:
            conn.execute('UPDATE quiz_sessions SET expires_at=?',((now()-timedelta(hours=3)).isoformat(),))
        self.assertEqual(self.client.post(endpoint,json={'position':1,'text':'hello'}).status_code,410)

    def test_profiles_custom_words_settings(self):
        wid=self.words()['items'][0]['id'];self.review(wid)
        body={'topic_id':1,'term':'testing phrase','meaning':'cụm từ kiểm thử','example':'This is a testing phrase.','level':'A2'}
        self.assertEqual(self.client.post('/api/words',json=body).status_code,201)
        self.assertEqual(self.client.post('/api/words',json=body).status_code,409)
        self.assertEqual(self.words()['total'],451)
        self.assertEqual(self.client.patch('/api/me',json={'name':'Minh','daily_goal':20}).status_code,200)
        self.assertEqual(self.client.get('/api/me').json()['daily_goal'],20)
        self.assertEqual(self.client.patch('/api/me',json={'name':' ','daily_goal':20}).status_code,422)
        other=TestClient(self.app)
        self.assertEqual(other.get('/api/stats').status_code,401)
        other.get('/api/me')
        self.assertEqual(other.get('/api/stats').json()['learned'],0)
        self.assertEqual(other.get('/api/words').json()['total'],450)
        custom=self.words(q='testing phrase')['items'][0]
        self.assertEqual(other.put(f"/api/words/{custom['id']}/bookmark",json={'saved':True}).status_code,404)

    def test_security_export(self):
        self.assertEqual(self.client.patch('/api/me',json={'name':'Hacker','daily_goal':20},headers={'Origin':'https://untrusted.example'}).status_code,403)
        self.assertEqual(self.client.get('/api/unknown').status_code,404)
        self.assertEqual(self.client.get('/api/health').json()['status'],'ok')
        self.review(self.words()['items'][0]['id'])
        data=self.client.get('/api/export').json()
        self.assertEqual(data['version'],1)
        self.assertEqual(len(data['events']),1)
        self.assertNotIn('id',data['profile'])
        self.assertNotIn('profile_id',data['progress'][0])

    def test_seed_idempotent(self):
        self.app.state.db.initialize()
        self.assertEqual(self.words()['total'],450)

    def test_concurrent_requests_have_separate_connections(self):
        with ThreadPoolExecutor(max_workers=6) as pool:
            responses=list(pool.map(lambda n:self.client.get('/api/stats' if n%2 else '/api/topics'),range(24)))
        self.assertTrue(all(r.status_code==200 for r in responses))

    def test_csv_import_atomic_and_idempotent(self):
        sample=Path(__file__).parent/'words-example.csv'
        self.assertEqual(import_csv(sample,self.app.state.db.path),3)
        self.assertEqual(import_csv(sample,self.app.state.db.path),0)
        self.assertEqual(self.words()['total'],453)
        invalid=Path(self.tmp.name)/'invalid.csv'
        invalid.write_text('topic_slug,term,meaning,example,level\nfood,new import,từ mới,A new import.,A1\nmissing,invalid,sai,An invalid line.,A1\n',encoding='utf-8')
        with self.assertRaises(ValueError):
            import_csv(invalid,self.app.state.db.path)
        self.assertEqual(self.words(q='new import')['total'],0)

    def test_public_https_origin_behind_proxy(self):
        with patch.dict('os.environ',{'LINGUA_PUBLIC_URL':'https://learn.example.com'}):
            hosted=create_app(Path(self.tmp.name)/'hosted.sqlite3')
        with TestClient(hosted) as client:
            response=client.get('/api/me')
            self.assertIn('Secure',response.headers['set-cookie'])
            # The proxy-facing request is HTTP; emulate forwarding the browser cookie.
            token=response.json()['id']
            headers={'Origin':'https://learn.example.com','Cookie':f'lingua_profile={token}'}
            self.assertEqual(client.patch('/api/me',json={'name':'Minh','daily_goal':15},headers=headers).status_code,200)
            headers['Origin']='https://other.example.com'
            self.assertEqual(client.patch('/api/me',json={'name':'Minh','daily_goal':15},headers=headers).status_code,403)
        with patch.dict('os.environ',{'LINGUA_PUBLIC_URL':'https://learn.example.com/path'}):
            with self.assertRaises(ValueError):
                create_app(Path(self.tmp.name)/'invalid.sqlite3')


if __name__=='__main__':
    unittest.main()
