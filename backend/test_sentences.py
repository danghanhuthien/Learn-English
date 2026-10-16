"""Integration tests for source preservation, additive migration and sentence learning."""
from datetime import timedelta
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from backend.app import create_app,now


class SentenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'learning.sqlite3'
        self.app=create_app(self.path)
        self.client=TestClient(self.app)
        self.client.__enter__()
        self.user=self.client.get('/api/me').json()

    def tearDown(self):
        self.client.__exit__(None,None,None)
        self.temp.cleanup()

    def review(self,sid='CB-001',rating='good',event='sentence-event-001',mode='study'):
        return self.client.post('/api/sentences/review',json={'sentence_id':sid,'rating':rating,'event_id':event,'mode':mode})

    def test_source_and_structure_preserved(self):
        meta=self.client.get('/api/sentences/meta').json()
        self.assertEqual(meta['total'],900)
        self.assertEqual(len(meta['topics']),10)
        self.assertEqual({l['name']:l['total'] for l in meta['levels']},{'A1':124,'A2':316,'B1':298,'B2':129,'C1':33})
        lessons=self.client.get('/api/sentences/lessons').json()
        self.assertEqual(len(lessons),90)
        self.assertTrue(all(l['total']==10 for l in lessons))
        seed=json.loads((Path(__file__).parent/'sentences_seed.json').read_text(encoding='utf-8'))['records']
        with self.app.state.db.connect() as conn:
            for source in seed:
                actual=dict(conn.execute('SELECT * FROM sentences WHERE id=?',(source['id'],)).fetchone())
                for key,value in source.items():
                    self.assertEqual(actual[key],value)
            self.assertEqual(conn.execute('SELECT count(DISTINCT english) FROM sentences').fetchone()[0],897)

    def test_filter_search_accent_insensitive_and_pagination(self):
        result=self.client.get('/api/sentences',params={'q':'chao hoi'}).json()
        self.assertGreater(result['total'],0)
        self.assertTrue(all('Chào hỏi'==r['situation'] for r in result['items']))
        self.assertEqual(self.client.get('/api/sentences?level=basic').json()['total'],440)
        self.assertEqual(self.client.get('/api/sentences?lesson=90').json()['total'],10)
        result=self.client.get('/api/sentences',params={'q':'CB-001'}).json()
        self.assertEqual(result['items'][0]['id'],'CB-001')
        percent=self.client.get('/api/sentences',params={'q':'%'}).json()
        self.assertTrue(all('%' in r['search_text'] for r in percent['items']))
        for needle in ["' OR 1=1 --"]:
            self.assertEqual(self.client.get('/api/sentences',params={'q':needle}).json()['total'],0)
        self.assertNotEqual(self.client.get('/api/sentences?page=1').json()['items'][0]['id'],self.client.get('/api/sentences?page=2').json()['items'][0]['id'])
        for query in ['page=0','page_size=999','lesson=91','level=invalid']:
            self.assertEqual(self.client.get('/api/sentences?'+query).status_code,422)

    def test_default_queue_and_resuming_half_lesson(self):
        queue=self.client.get('/api/sentences/queue').json()['items']
        self.assertEqual(len(queue),5)
        self.assertEqual(queue[0]['id'],'CB-001')
        self.assertTrue(all(r['level'] in {'A1','A2'} for r in queue))
        first=self.client.get('/api/sentences/queue?mode=lesson&lesson=1&level=').json()['items']
        for i,row in enumerate(first):
            self.assertEqual(self.review(row['id'],event=f'lesson-event-{i:03}').status_code,200)
        second=self.client.get('/api/sentences/queue?mode=lesson&lesson=1&level=').json()['items']
        self.assertTrue(set(r['id'] for r in first).isdisjoint(set(r['id'] for r in second)))
        for i,row in enumerate(second):self.review(row['id'],event=f'lesson-other-{i:03}')
        stats=self.client.get('/api/sentences/stats').json()
        self.assertEqual(stats['completed_lessons'],1)

    def test_daily_cap_and_goal_separate_from_vocabulary(self):
        queue=self.client.get('/api/sentences/queue?limit=10').json()['items']
        self.assertEqual(len(queue),5)
        for i,row in enumerate(queue):self.review(row['id'],event=f'daily-goal-{i:03}')
        self.assertEqual(self.client.get('/api/sentences/queue').json()['items'],[])
        stats=self.client.get('/api/sentences/stats').json()
        self.assertEqual(stats['today_new'],5)
        self.assertEqual(stats['streak'],1)
        self.assertEqual(self.client.get('/api/stats').json()['learned'],0)
        self.assertEqual(self.client.get('/api/stats').json()['today_words'],0)
        self.assertEqual(self.client.patch('/api/sentences/settings',json={'daily_goal':10}).status_code,200)
        self.assertEqual(len(self.client.get('/api/sentences/queue?limit=10').json()['items']),5)
        self.assertEqual(self.client.get('/api/me').json()['daily_goal'],15)
        self.assertEqual(self.client.patch('/api/sentences/settings',json={'daily_goal':100}).status_code,422)

    def test_schedule_retries_and_modes(self):
        self.assertEqual(self.review().json()['interval_days'],1)
        self.assertEqual(self.review().json()['stage'],1)
        self.assertEqual(self.review(rating='easy').status_code,409)
        for n,days in [(2,3),(3,7),(4,14)]:
            result=self.review(event=f'review-step-{n:03}',mode='recall').json()
            self.assertEqual(result['interval_days'],days)
        self.assertEqual(self.client.get('/api/sentences/stats').json()['mastered'],1)
        self.assertEqual(self.review(rating='hard',event='review-hard-001').json()['interval_days'],7)
        self.assertEqual(self.client.get('/api/sentences/stats').json()['mastered'],0)
        self.assertEqual(self.review(rating='again',event='review-again-001',mode='response').json()['stage'],0)
        stats=self.client.get('/api/sentences/stats').json()
        self.assertEqual(stats['today_new'],1)
        self.assertEqual(stats['today_sentences'],1)
        self.assertEqual(stats['today_reviews'],6)
        self.assertEqual({m['mode'] for m in stats['modes']},{'study','recall','response'})

    def test_due_backlog_is_prioritized_and_pauses_new(self):
        rows=self.client.get('/api/sentences?page_size=25').json()['items']
        for i,row in enumerate(rows):self.review(row['id'],event=f'backlog-event-{i:03}')
        with self.app.state.db.connect() as conn:
            conn.execute('UPDATE sentence_progress SET due_at=?',((now()-timedelta(minutes=2)).isoformat(),))
        queue=self.client.get('/api/sentences/queue').json()
        self.assertEqual(len(queue['items']),20)
        self.assertTrue(all(r['last_rating'] for r in queue['items']))
        self.assertEqual(queue['due_remaining'],5)
        self.assertEqual(len(self.client.get('/api/sentences/queue?mode=due').json()['items']),20)

    def test_notes_bookmarks_and_profile_isolation(self):
        result=self.client.put('/api/sentences/CB-001/note',json={'saved':True,'note':'Dùng khi gặp đồng nghiệp.'})
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.client.get('/api/sentences?status=saved').json()['total'],1)
        self.assertEqual(self.client.get('/api/sentences/stats').json()['learned'],0)
        self.review()
        other=TestClient(self.app)
        self.assertEqual(other.get('/api/sentences').status_code,401)
        other.get('/api/me')
        self.assertEqual(other.get('/api/sentences?status=saved').json()['total'],0)
        self.assertEqual(other.get('/api/sentences/stats').json()['learned'],0)
        self.assertEqual(other.post('/api/sentences/review',json={'sentence_id':'CB-001','event_id':'sentence-event-001','rating':'good'}).status_code,409)
        other.close()
        self.assertEqual(self.client.get('/api/sentences/queue?mode=single&sentence_id=CB-001').json()['items'][0]['note'],'Dùng khi gặp đồng nghiệp.')
        self.assertEqual(self.client.put('/api/sentences/missing/note',json={'saved':True}).status_code,404)
        self.assertEqual(self.review(sid='missing',event='missing-item-001').status_code,404)

    def test_export_contains_sentence_progress_without_cookie(self):
        self.review()
        self.client.put('/api/sentences/CB-001/note',json={'note':'Ghi chú riêng'})
        result=self.client.get('/api/export').json()['sentences']
        self.assertEqual(result['daily_goal'],5)
        self.assertEqual(result['progress'][0]['note'],'Ghi chú riêng')
        self.assertEqual(len(result['events']),1)
        self.assertNotIn(self.user['id'],json.dumps(result))

    def test_learning_streak_combines_days_without_mixing_word_counts(self):
        self.review()
        self.client.post('/api/review',json={'word_id':1,'rating':'good','event_id':'streak-word-001'})
        with self.app.state.db.connect() as conn:
            conn.execute('UPDATE events SET day=? WHERE id=?',((now().date()-timedelta(days=1)).isoformat(),'streak-word-001'))
        stats=self.client.get('/api/stats').json()
        self.assertEqual(stats['learning_streak'],2)
        self.assertEqual(stats['today_words'],0)
        self.assertEqual(stats['learned'],1)
        self.assertEqual(self.client.get('/api/sentences/stats').json()['streak'],1)

    def test_additive_upgrade_backs_up_and_preserves_existing_data(self):
        self.client.post('/api/review',json={'word_id':1,'rating':'easy','event_id':'original-word-event'})
        self.client.patch('/api/me',json={'name':'Original learner','daily_goal':20})
        self.client.post('/api/words',json={'topic_id':1,'term':'custom phrase','meaning':'câu riêng','example':'A custom phrase.','level':'A2'})
        self.client.post('/api/quiz',json={'count':5})
        original_tables=['profiles','words','topics','progress','events','quiz_sessions','quiz_answers']
        with self.app.state.db.connect() as conn:
            snapshot={table:[tuple(r) for r in conn.execute('SELECT * FROM '+table+' ORDER BY rowid')] for table in original_tables}
            for table in ['sentence_events','sentence_progress','sentence_settings','sentences']:
                conn.execute('DROP TABLE '+table)
            conn.execute('PRAGMA user_version=1')
        self.app.state.db.initialize()
        with self.app.state.db.connect() as conn:
            for table in original_tables:
                self.assertEqual([tuple(r) for r in conn.execute('SELECT * FROM '+table+' ORDER BY rowid')],snapshot[table])
            self.assertEqual(conn.execute('PRAGMA user_version').fetchone()[0],2)
        self.assertEqual(len(list((self.path.parent/'backups').glob('*.sqlite3'))),1)
        self.app.state.db.initialize()
        self.assertEqual(len(list((self.path.parent/'backups').glob('*.sqlite3'))),1)
        self.assertEqual(self.client.get('/api/sentences/meta').json()['total'],900)
        self.assertEqual(self.client.get('/api/me').json()['name'],'Original learner')


if __name__=='__main__':
    unittest.main()
