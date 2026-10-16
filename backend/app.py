"""Lingua: local-first vocabulary learning API and built Vue application."""
from contextlib import asynccontextmanager, contextmanager, closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import json
import os
import random
import secrets
import sqlite3
import unicodedata
from urllib.parse import urlsplit

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from backend.sentences import initialize_sentences, register_sentences, export_sentences

BASE = Path(__file__).resolve().parent
DIST = BASE.parent / 'frontend' / 'dist'
try:
    LOCAL_TZ = ZoneInfo(os.getenv('LINGUA_TIMEZONE', 'Asia/Bangkok'))
except ZoneInfoNotFoundError:
    from datetime import timezone
    LOCAL_TZ = timezone(timedelta(hours=7))


def now():
    return datetime.now(LOCAL_TZ)


def normalize(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().strip().split())


class Settings(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    daily_goal: int = Field(ge=5, le=100)


class Review(BaseModel):
    word_id: int
    rating: Literal['again', 'hard', 'good', 'easy']
    event_id: str = Field(min_length=8, max_length=80)


class Bookmark(BaseModel):
    saved: bool


class QuizStart(BaseModel):
    topic_id: int | None = None
    count: int = Field(default=10, ge=5, le=20)
    mode: Literal['choice', 'typing'] = 'choice'


class QuizAnswer(BaseModel):
    position: int = Field(ge=0)
    option_id: int | None = None
    text: str | None = Field(default=None, max_length=200)


class NewWord(BaseModel):
    topic_id: int
    term: str = Field(min_length=1, max_length=100)
    meaning: str = Field(min_length=1, max_length=200)
    example: str = Field(min_length=1, max_length=300)
    level: Literal['A1', 'A2', 'B1', 'B2'] = 'A1'


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS profiles (
 id TEXT PRIMARY KEY, name TEXT NOT NULL DEFAULT 'Bạn',
 daily_goal INTEGER NOT NULL DEFAULT 15, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS topics (
 id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 category TEXT NOT NULL, description TEXT NOT NULL, icon TEXT NOT NULL,
 color TEXT NOT NULL, level TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS words (
 id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL REFERENCES topics(id),
 term TEXT NOT NULL COLLATE NOCASE, meaning TEXT NOT NULL,
 example TEXT NOT NULL, level TEXT NOT NULL, owner_id TEXT REFERENCES profiles(id),
 UNIQUE(topic_id, term, owner_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS seed_word_unique ON words(topic_id, term) WHERE owner_id IS NULL;
CREATE TABLE IF NOT EXISTS progress (
 profile_id TEXT NOT NULL REFERENCES profiles(id), word_id INTEGER NOT NULL REFERENCES words(id),
 repetitions INTEGER NOT NULL DEFAULT 0, interval_days INTEGER NOT NULL DEFAULT 0,
 due_at TEXT, saved INTEGER NOT NULL DEFAULT 0, last_rating TEXT,
 PRIMARY KEY(profile_id,word_id)
);
CREATE TABLE IF NOT EXISTS events (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id),
 word_id INTEGER NOT NULL REFERENCES words(id), kind TEXT NOT NULL,
 rating TEXT NOT NULL, correct INTEGER, created_at TEXT NOT NULL, day TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS events_profile_day ON events(profile_id,day);
CREATE INDEX IF NOT EXISTS progress_due ON progress(profile_id,due_at);
CREATE INDEX IF NOT EXISTS words_topic ON words(topic_id);
CREATE TABLE IF NOT EXISTS quiz_sessions (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id),
 mode TEXT NOT NULL, items TEXT NOT NULL, expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS quiz_answers (
 session_id TEXT NOT NULL REFERENCES quiz_sessions(id), position INTEGER NOT NULL,
 result TEXT NOT NULL, PRIMARY KEY(session_id,position)
);
"""


class Database:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        # FastAPI may schedule a sync dependency and its route on different workers.
        # Each request owns its connection; transactions are never shared by requests.
        conn = sqlite3.connect(self.path, timeout=15, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys=ON')
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        seed = json.loads((BASE / 'seed.json').read_text(encoding='utf-8'))
        with self.connect() as conn:
            version=conn.execute('PRAGMA user_version').fetchone()[0]
            has_tables=conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='profiles'").fetchone()
            if has_tables and version<2:
                backup_dir=self.path.parent/'backups'
                backup_dir.mkdir(exist_ok=True)
                backup_path=backup_dir/f'{self.path.stem}-before-v2-{now().strftime("%Y%m%d-%H%M%S-%f")}.sqlite3'
                with closing(sqlite3.connect(backup_path)) as backup:
                    conn.backup(backup)
            conn.executescript(SCHEMA)
            for topic in seed:
                conn.execute('INSERT OR IGNORE INTO topics(slug,name,category,description,icon,color,level) VALUES(?,?,?,?,?,?,?)',
                             tuple(topic[k] for k in ('slug','name','category','description','icon','color','level')))
                topic_id = conn.execute('SELECT id FROM topics WHERE slug=?', (topic['slug'],)).fetchone()['id']
                for word in topic['words']:
                    conn.execute('INSERT OR IGNORE INTO words(topic_id,term,meaning,example,level) VALUES(?,?,?,?,?)',
                                 (topic_id,word['term'],word['meaning'],word['example'],word.get('level',topic['level'])))
            initialize_sentences(conn)


def apply_review(conn, profile, word_id, rating, event_id, kind='study', correct=None):
    """Small transparent spaced-review schedule. Transaction owned by caller."""
    previous = conn.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
    if previous:
        if previous['profile_id'] != profile or previous['word_id'] != word_id or previous['rating'] != rating or previous['kind'] != kind:
            raise HTTPException(409, 'Mã lượt học đã được dùng cho một thao tác khác.')
        return dict(conn.execute('SELECT * FROM progress WHERE profile_id=? AND word_id=?', (profile,word_id)).fetchone())
    old = conn.execute('SELECT * FROM progress WHERE profile_id=? AND word_id=?', (profile,word_id)).fetchone()
    reps, interval = (old['repetitions'],old['interval_days']) if old else (0,0)
    if rating == 'again':
        reps, interval = 0, 0
        due = now() + timedelta(minutes=10)
    else:
        reps += 1
        interval = {'hard':max(1,round(interval*1.2)), 'good':max(1,round(interval*2.2)), 'easy':max(3,round(interval*3))}[rating]
        interval = min(interval,180)
        due = now() + timedelta(days=interval)
    conn.execute('''INSERT INTO progress(profile_id,word_id,repetitions,interval_days,due_at,last_rating)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(profile_id,word_id) DO UPDATE SET
                    repetitions=excluded.repetitions,interval_days=excluded.interval_days,
                    due_at=excluded.due_at,last_rating=excluded.last_rating''',
                 (profile,word_id,reps,interval,due.isoformat(),rating))
    timestamp = now()
    conn.execute('INSERT INTO events VALUES(?,?,?,?,?,?,?,?)',
                 (event_id,profile,word_id,kind,rating,correct,timestamp.isoformat(),timestamp.date().isoformat()))
    return dict(conn.execute('SELECT * FROM progress WHERE profile_id=? AND word_id=?',(profile,word_id)).fetchone())


def create_app(db_path=None):
    db = Database(db_path or os.getenv('LINGUA_DB',str(BASE/'data'/'lingua.sqlite3')))
    public_url = os.getenv('LINGUA_PUBLIC_URL','').strip().rstrip('/')
    if public_url:
        parsed = urlsplit(public_url)
        if parsed.scheme not in {'http','https'} or not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError('LINGUA_PUBLIC_URL cần là origin đầy đủ, ví dụ https://learn.example.com (không có đường dẫn).')

    @asynccontextmanager
    async def lifespan(app):
        db.initialize()
        yield

    app = FastAPI(title='Lingua API',version='2.0.0',lifespan=lifespan)
    app.state.db = db

    @app.middleware('http')
    async def same_origin(request: Request, call_next):
        origin = request.headers.get('origin')
        allowed = {str(request.base_url).rstrip('/'), 'http://127.0.0.1:5173', 'http://localhost:5173'}
        if public_url:
            allowed.add(public_url)
        if request.method in {'POST','PUT','PATCH','DELETE'} and origin and origin not in allowed:
            return Response('Cross-origin writes are not allowed.',status_code=403)
        response = await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    def connection():
        with db.connect() as conn:
            yield conn

    def profile(request: Request, conn=Depends(connection)):
        token = request.cookies.get('lingua_profile','')
        row = conn.execute('SELECT * FROM profiles WHERE id=?',(token,)).fetchone()
        if not row:
            raise HTTPException(401,'Hãy tải lại trang để khởi tạo hồ sơ học.')
        return dict(row)

    def word_for_user(conn, word_id, user):
        row = conn.execute('SELECT * FROM words WHERE id=? AND (owner_id IS NULL OR owner_id=?)',(word_id,user['id'])).fetchone()
        if not row:
            raise HTTPException(404,'Không tìm thấy từ vựng.')
        return row

    @app.get('/api/health')
    def health():
        return {'status':'ok'}

    @app.get('/api/me')
    def me(request: Request, response: Response, conn=Depends(connection)):
        token = request.cookies.get('lingua_profile','')
        row = conn.execute('SELECT * FROM profiles WHERE id=?',(token,)).fetchone()
        if not row:
            token = secrets.token_urlsafe(32)
            conn.execute('INSERT INTO profiles(id,created_at) VALUES(?,?)',(token,now().isoformat()))
            row = conn.execute('SELECT * FROM profiles WHERE id=?',(token,)).fetchone()
            response.set_cookie('lingua_profile',token,httponly=True,samesite='strict',secure=request.url.scheme=='https' or public_url.startswith('https://'),max_age=31536000)
        return dict(row)

    @app.patch('/api/me')
    def update_me(body: Settings, user=Depends(profile), conn=Depends(connection)):
        name = body.name.strip()
        if not name:
            raise HTTPException(422,'Tên không được để trống.')
        conn.execute('UPDATE profiles SET name=?,daily_goal=? WHERE id=?',(name,body.daily_goal,user['id']))
        return dict(conn.execute('SELECT * FROM profiles WHERE id=?',(user['id'],)).fetchone())

    @app.get('/api/topics')
    def topics(user=Depends(profile),conn=Depends(connection)):
        return [dict(row) for row in conn.execute('''SELECT t.*,count(w.id) word_count,
            coalesce(sum(CASE WHEN p.last_rating IS NOT NULL THEN 1 ELSE 0 END),0) learned_count,
            coalesce(sum(CASE WHEN p.repetitions>=3 AND p.interval_days>=7 THEN 1 ELSE 0 END),0) mastered_count
            FROM topics t LEFT JOIN words w ON w.topic_id=t.id AND (w.owner_id IS NULL OR w.owner_id=?)
            LEFT JOIN progress p ON p.word_id=w.id AND p.profile_id=? GROUP BY t.id ORDER BY t.id''',(user['id'],user['id']))]

    def word_query():
        return '''SELECT w.*,t.name topic_name,t.color topic_color,coalesce(p.saved,0) saved,
           coalesce(p.repetitions,0) repetitions,coalesce(p.interval_days,0) interval_days,p.last_rating,p.due_at
           FROM words w JOIN topics t ON t.id=w.topic_id
           LEFT JOIN progress p ON p.word_id=w.id AND p.profile_id=?
           WHERE (w.owner_id IS NULL OR w.owner_id=?)'''

    @app.get('/api/words')
    def words(topic_id: int | None=None,q: str='',status: str='all',level: str='',page: int=1,page_size: int=24,
              user=Depends(profile),conn=Depends(connection)):
        if page<1 or not 1<=page_size<=100 or status not in {'all','saved','new','learned','mastered'}:
            raise HTTPException(422,'Bộ lọc hoặc phân trang chưa hợp lệ.')
        sql,args = word_query(),[user['id'],user['id']]
        if topic_id is not None:
            sql+=' AND w.topic_id=?'; args.append(topic_id)
        if q.strip():
            escaped=q.strip().replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            sql+=" AND (w.term LIKE ? ESCAPE '\\' OR w.meaning LIKE ? ESCAPE '\\')"; args.extend([f'%{escaped}%']*2)
        if level:
            sql+=' AND w.level=?'; args.append(level)
        sql += {'all':'','saved':' AND p.saved=1','new':' AND p.last_rating IS NULL','learned':' AND p.last_rating IS NOT NULL','mastered':' AND p.repetitions>=3 AND p.interval_days>=7'}[status]
        total=conn.execute('SELECT count(*) FROM ('+sql+')',args).fetchone()[0]
        rows=conn.execute(sql+' ORDER BY w.id LIMIT ? OFFSET ?',args+[page_size,(page-1)*page_size])
        return {'items':[dict(r) for r in rows],'total':total,'page':page,'page_size':page_size}

    @app.post('/api/words',status_code=201)
    def add_word(body: NewWord,user=Depends(profile),conn=Depends(connection)):
        if not conn.execute('SELECT id FROM topics WHERE id=?',(body.topic_id,)).fetchone():
            raise HTTPException(404,'Chủ đề không tồn tại.')
        term,meaning,example=(v.strip() for v in (body.term,body.meaning,body.example))
        if not all((term,meaning,example)):
            raise HTTPException(422,'Vui lòng điền đầy đủ từ, nghĩa và câu ví dụ.')
        if conn.execute('SELECT id FROM words WHERE topic_id=? AND term=? AND (owner_id IS NULL OR owner_id=?)',(body.topic_id,term,user['id'])).fetchone():
            raise HTTPException(409,'Từ này đã có trong chủ đề.')
        cursor=conn.execute('INSERT INTO words(topic_id,term,meaning,example,level,owner_id) VALUES(?,?,?,?,?,?)',
                            (body.topic_id,term,meaning,example,body.level,user['id']))
        return dict(word_for_user(conn,cursor.lastrowid,user))

    @app.put('/api/words/{word_id}/bookmark')
    def bookmark(word_id: int,body: Bookmark,user=Depends(profile),conn=Depends(connection)):
        word_for_user(conn,word_id,user)
        conn.execute('INSERT INTO progress(profile_id,word_id,saved) VALUES(?,?,?) ON CONFLICT(profile_id,word_id) DO UPDATE SET saved=excluded.saved',
                     (user['id'],word_id,int(body.saved)))
        return {'saved':body.saved}

    @app.get('/api/review')
    def review_queue(topic_id: int | None=None,mode: Literal['due','new','mixed','saved']='mixed',limit: int=20,
                     user=Depends(profile),conn=Depends(connection)):
        if not 1<=limit<=50:
            raise HTTPException(422,'Mỗi lượt học cần từ 1 đến 50 từ.')
        sql,args=word_query(),[user['id'],user['id']]
        if topic_id is not None:
            sql+=' AND w.topic_id=?'; args.append(topic_id)
        if mode=='due':
            sql+=' AND p.due_at<=?'; args.append(now().isoformat())
        elif mode=='new':
            sql+=' AND p.last_rating IS NULL'
        elif mode=='saved':
            sql+=' AND p.saved=1'
        else:
            sql+=' AND (p.last_rating IS NULL OR p.due_at<=?)'; args.append(now().isoformat())
        sql+=' ORDER BY CASE WHEN p.last_rating IS NOT NULL THEN 0 ELSE 1 END,p.due_at,w.id LIMIT ?'; args.append(limit)
        return [dict(r) for r in conn.execute(sql,args)]

    @app.post('/api/review')
    def review(body: Review,user=Depends(profile),conn=Depends(connection)):
        word_for_user(conn,body.word_id,user)
        conn.execute('BEGIN IMMEDIATE')
        return apply_review(conn,user['id'],body.word_id,body.rating,body.event_id)

    @app.get('/api/stats')
    def stats(user=Depends(profile),conn=Depends(connection)):
        pid=user['id']; today=now().date()
        counts=dict(conn.execute('''SELECT count(*) learned,
            coalesce(sum(CASE WHEN repetitions>=3 AND interval_days>=7 THEN 1 ELSE 0 END),0) mastered,
            coalesce(sum(CASE WHEN due_at<=? THEN 1 ELSE 0 END),0) due
            FROM progress WHERE profile_id=? AND last_rating IS NOT NULL''',(now().isoformat(),pid)).fetchone())
        days={r['day']:dict(r) for r in conn.execute('SELECT day,count(*) reviews,count(DISTINCT word_id) words FROM events WHERE profile_id=? GROUP BY day',(pid,))}
        streak=0; cursor=today if today.isoformat() in days else today-timedelta(days=1)
        while cursor.isoformat() in days:
            streak+=1; cursor-=timedelta(days=1)
        learning_days=set(days)|{r[0] for r in conn.execute('SELECT DISTINCT day FROM sentence_events WHERE profile_id=?',(pid,))}
        learning_streak=0;cursor=today if today.isoformat() in learning_days else today-timedelta(days=1)
        while cursor.isoformat() in learning_days:
            learning_streak+=1;cursor-=timedelta(days=1)
        totals=conn.execute('SELECT count(*) total,sum(correct) correct FROM events WHERE profile_id=? AND kind=?',(pid,'quiz')).fetchone()
        activity=[]
        for offset in range(6,-1,-1):
            day=today-timedelta(days=offset)
            activity.append({'day':day.isoformat(),'label':day.strftime('%d/%m'),**days.get(day.isoformat(),{'reviews':0,'words':0})})
        return {**counts,'total_words':conn.execute('SELECT count(*) FROM words WHERE owner_id IS NULL OR owner_id=?',(pid,)).fetchone()[0],
                'today_words':days.get(today.isoformat(),{}).get('words',0),'today_reviews':days.get(today.isoformat(),{}).get('reviews',0),
                'daily_goal':user['daily_goal'],'streak':streak,'learning_streak':learning_streak,'quiz_answers':totals['total'],
                'accuracy':round((totals['correct'] or 0)/totals['total']*100) if totals['total'] else None,'activity':activity}

    @app.post('/api/quiz')
    def start_quiz(body: QuizStart,user=Depends(profile),conn=Depends(connection)):
        sql='SELECT * FROM words WHERE (owner_id IS NULL OR owner_id=?)'; args=[user['id']]
        if body.topic_id is not None:
            sql+=' AND topic_id=?'; args.append(body.topic_id)
        pool=[dict(r) for r in conn.execute(sql,args)]
        if len(pool)<4:
            raise HTTPException(400,'Cần ít nhất 4 từ để tạo bài luyện tập.')
        selected=random.sample(pool,min(body.count,len(pool)))
        items=[]; public=[]
        for pos,word in enumerate(selected):
            candidates=[r for r in pool if r['id']!=word['id'] and r['meaning']!=word['meaning']]
            random.shuffle(candidates)
            unique={word['meaning']}
            choices=[{'id':word['id'],'label':word['meaning']}]
            for other in candidates:
                if other['meaning'] not in unique:
                    choices.append({'id':other['id'],'label':other['meaning']}); unique.add(other['meaning'])
                if len(choices)==4:
                    break
            if body.mode=='choice' and len(choices)<4:
                raise HTTPException(400,'Cần ít nhất 4 nghĩa khác nhau trong chủ đề.')
            random.shuffle(choices)
            items.append({'word_id':word['id'],'options':[c['id'] for c in choices]})
            public.append({'position':pos,'prompt':word['term'] if body.mode=='choice' else word['meaning'],
                           'options':choices if body.mode=='choice' else []})
        session=secrets.token_urlsafe(24)
        conn.execute('DELETE FROM quiz_sessions WHERE expires_at<? AND id NOT IN (SELECT session_id FROM quiz_answers)',(now().isoformat(),))
        conn.execute('INSERT INTO quiz_sessions VALUES(?,?,?,?,?)',(session,user['id'],body.mode,json.dumps(items),(now()+timedelta(hours=2)).isoformat()))
        return {'id':session,'mode':body.mode,'questions':public}

    @app.post('/api/quiz/{session_id}/answer')
    def answer_quiz(session_id: str,body: QuizAnswer,user=Depends(profile),conn=Depends(connection)):
        conn.execute('BEGIN IMMEDIATE')
        session=conn.execute('SELECT * FROM quiz_sessions WHERE id=? AND profile_id=?',(session_id,user['id'])).fetchone()
        if not session:
            raise HTTPException(404,'Không tìm thấy bài luyện tập.')
        previous=conn.execute('SELECT result FROM quiz_answers WHERE session_id=? AND position=?',(session_id,body.position)).fetchone()
        if previous:
            return json.loads(previous['result'])
        if session['expires_at']<now().isoformat():
            raise HTTPException(410,'Bài luyện tập đã hết hạn. Hãy bắt đầu bài mới.')
        items=json.loads(session['items'])
        if body.position>=len(items):
            raise HTTPException(422,'Câu hỏi không hợp lệ.')
        item=items[body.position]; word=word_for_user(conn,item['word_id'],user)
        if session['mode']=='choice':
            if body.option_id not in item['options']:
                raise HTTPException(422,'Đáp án không nằm trong các lựa chọn.')
            correct=body.option_id==word['id']
        else:
            if not body.text or not body.text.strip():
                raise HTTPException(422,'Hãy nhập câu trả lời.')
            correct=normalize(body.text)==normalize(word['term'])
        result={'correct':correct,'word':dict(word)}
        apply_review(conn,user['id'],word['id'],'good' if correct else 'again',f'quiz:{session_id}:{body.position}','quiz',int(correct))
        conn.execute('INSERT INTO quiz_answers VALUES(?,?,?)',(session_id,body.position,json.dumps(result)))
        return result

    @app.get('/api/export')
    def export(user=Depends(profile),conn=Depends(connection)):
        return {'version':1,'exported_at':now().isoformat(),'profile':{'name':user['name'],'daily_goal':user['daily_goal']},
                'progress':[dict(r) for r in conn.execute('SELECT p.word_id,p.repetitions,p.interval_days,p.due_at,p.saved,p.last_rating,w.term,w.meaning,t.slug topic FROM progress p JOIN words w ON w.id=p.word_id JOIN topics t ON t.id=w.topic_id WHERE p.profile_id=?',(user['id'],))],
                'custom_words':[dict(r) for r in conn.execute('SELECT term,meaning,example,level,topic_id FROM words WHERE owner_id=?',(user['id'],))],
                'events':[dict(r) for r in conn.execute('SELECT word_id,kind,rating,correct,created_at,day FROM events WHERE profile_id=?',(user['id'],))],
                'sentences':export_sentences(conn,user['id'])}

    register_sentences(app,connection,profile,now)

    # Register API routes before SPA fallback; never turn missing APIs into HTML.
    @app.get('/api/{path:path}')
    def missing_api(path: str):
        raise HTTPException(404,'API không tồn tại.')

    if (DIST/'assets').exists():
        app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')

    @app.get('/{path:path}',include_in_schema=False)
    def frontend(path: str):
        requested=(DIST/path).resolve()
        if requested.is_relative_to(DIST.resolve()) and requested.is_file():
            return FileResponse(requested)
        if (DIST/'index.html').exists():
            return FileResponse(DIST/'index.html')
        raise HTTPException(503,'Chưa có giao diện đã build. Chạy npm run build trong frontend hoặc dùng Vite ở cổng 5173.')

    return app


app=create_app()
