"""Sentence learning, deliberately separate from vocabulary progress and goals."""
from datetime import timedelta
import json
from pathlib import Path
import unicodedata

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Literal

SCHEMA='''
CREATE TABLE IF NOT EXISTS sentences (
 id TEXT PRIMARY KEY, level TEXT NOT NULL, topic TEXT NOT NULL, english TEXT NOT NULL,
 vietnamese TEXT NOT NULL, reply_text TEXT NOT NULL, reply_english TEXT NOT NULL,
 reply_vietnamese TEXT NOT NULL, situation TEXT NOT NULL, context TEXT NOT NULL,
 lesson INTEGER NOT NULL, source TEXT NOT NULL, source_index INTEGER NOT NULL,
 source_row INTEGER NOT NULL, sort_order INTEGER NOT NULL UNIQUE, search_text TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sentences_lesson ON sentences(lesson,sort_order);
CREATE TABLE IF NOT EXISTS sentence_settings (
 profile_id TEXT PRIMARY KEY REFERENCES profiles(id), daily_goal INTEGER NOT NULL DEFAULT 5
);
CREATE TABLE IF NOT EXISTS sentence_progress (
 profile_id TEXT NOT NULL REFERENCES profiles(id), sentence_id TEXT NOT NULL REFERENCES sentences(id),
 stage INTEGER NOT NULL DEFAULT 0, interval_days INTEGER NOT NULL DEFAULT 0, due_at TEXT,
 last_rating TEXT, saved INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '',
 PRIMARY KEY(profile_id,sentence_id)
);
CREATE INDEX IF NOT EXISTS sentence_progress_due ON sentence_progress(profile_id,due_at);
CREATE TABLE IF NOT EXISTS sentence_events (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES profiles(id), sentence_id TEXT NOT NULL REFERENCES sentences(id),
 mode TEXT NOT NULL, rating TEXT NOT NULL, is_new INTEGER NOT NULL, created_at TEXT NOT NULL, day TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sentence_events_day ON sentence_events(profile_id,day);
'''


def search_key(value):
    return ''.join(c for c in unicodedata.normalize('NFD',value.casefold().replace('đ','d')) if unicodedata.category(c)!='Mn')


def initialize_sentences(conn):
    # CREATE IF NOT EXISTS only: never rebuild or replace existing learning tables.
    conn.executescript(SCHEMA)
    payload=json.loads((Path(__file__).parent/'sentences_seed.json').read_text(encoding='utf-8'))
    fields=('id','level','topic','english','vietnamese','reply_text','reply_english','reply_vietnamese',
            'situation','context','lesson','source','source_index','source_row','sort_order')
    for row in payload['records']:
        searchable=search_key(' '.join(str(row[k]) for k in ('id','english','vietnamese','reply_text','topic','situation','context')))
        conn.execute(f'INSERT OR IGNORE INTO sentences({",".join(fields)},search_text) VALUES({",".join(["?"]*16)})',
                     [row[k] for k in fields]+[searchable])
    conn.execute('PRAGMA user_version=2')


class SentencePreferences(BaseModel):
    daily_goal: Literal[5,10] = 5


class SentenceReview(BaseModel):
    sentence_id: str = Field(min_length=1,max_length=30)
    event_id: str = Field(min_length=8,max_length=80)
    rating: Literal['again','hard','good','easy']
    mode: Literal['study','recall','response'] = 'study'


class SentenceNote(BaseModel):
    saved: bool | None = None
    note: str | None = Field(default=None,max_length=1500)


def export_sentences(conn,pid):
    preference=conn.execute('SELECT daily_goal FROM sentence_settings WHERE profile_id=?',(pid,)).fetchone()
    return {'daily_goal':preference['daily_goal'] if preference else 5,
            'progress':[dict(r) for r in conn.execute('SELECT sentence_id,stage,interval_days,due_at,last_rating,saved,note FROM sentence_progress WHERE profile_id=?',(pid,))],
            'events':[dict(r) for r in conn.execute('SELECT sentence_id,mode,rating,is_new,created_at,day FROM sentence_events WHERE profile_id=? ORDER BY created_at',(pid,))]}


def register_sentences(app,connection,profile,clock):
    def goal(conn,pid):
        row=conn.execute('SELECT daily_goal FROM sentence_settings WHERE profile_id=?',(pid,)).fetchone()
        return row['daily_goal'] if row else 5

    def base_query():
        return '''SELECT s.*,coalesce(p.stage,0) stage,coalesce(p.interval_days,0) interval_days,
          p.due_at,p.last_rating,coalesce(p.saved,0) saved,coalesce(p.note,'') note
          FROM sentences s LEFT JOIN sentence_progress p ON p.sentence_id=s.id AND p.profile_id=? WHERE 1=1'''

    def row_for(conn,pid,sid):
        row=conn.execute(base_query()+' AND s.id=?',(pid,sid)).fetchone()
        if not row:
            raise HTTPException(404,'Không tìm thấy câu giao tiếp.')
        return dict(row)

    def filter_sql(topic,level,context,lesson):
        sql='';args=[]
        for column,value in [('topic',topic),('context',context),('lesson',lesson)]:
            if value is not None and value!='':
                sql+=f' AND s.{column}=?';args.append(value)
        if level:
            levels=['A1','A2'] if level=='basic' else [level]
            sql+=' AND s.level IN ('+','.join('?' for _ in levels)+')';args.extend(levels)
        return sql,args

    @app.get('/api/sentences/meta')
    def metadata(user=Depends(profile),conn=Depends(connection)):
        return {'total':conn.execute('SELECT count(*) FROM sentences').fetchone()[0],
                'topics':[dict(r) for r in conn.execute('SELECT topic name,count(*) total FROM sentences GROUP BY topic ORDER BY min(sort_order)')],
                'contexts':[r[0] for r in conn.execute('SELECT DISTINCT context FROM sentences ORDER BY context')],
                'levels':[dict(r) for r in conn.execute('SELECT level name,count(*) total FROM sentences GROUP BY level ORDER BY level')],
                'daily_goal':goal(conn,user['id'])}

    @app.patch('/api/sentences/settings')
    def settings(body: SentencePreferences,user=Depends(profile),conn=Depends(connection)):
        conn.execute('INSERT INTO sentence_settings VALUES(?,?) ON CONFLICT(profile_id) DO UPDATE SET daily_goal=excluded.daily_goal',
                     (user['id'],body.daily_goal))
        return {'daily_goal':body.daily_goal}

    @app.get('/api/sentences/stats')
    def stats(user=Depends(profile),conn=Depends(connection)):
        pid=user['id'];today=clock().date();stamp=clock().isoformat()
        learned=conn.execute('''SELECT count(*) learned,coalesce(sum(CASE WHEN stage>=4 AND interval_days>=14 THEN 1 ELSE 0 END),0) mastered,
            coalesce(sum(CASE WHEN due_at<=? THEN 1 ELSE 0 END),0) due FROM sentence_progress WHERE profile_id=? AND last_rating IS NOT NULL''',(stamp,pid)).fetchone()
        days={r['day']:dict(r) for r in conn.execute('''SELECT day,count(*) reviews,count(DISTINCT sentence_id) sentences,
            sum(is_new) new_sentences FROM sentence_events WHERE profile_id=? GROUP BY day''',(pid,))}
        streak=0;cursor=today if today.isoformat() in days else today-timedelta(days=1)
        while cursor.isoformat() in days:
            streak+=1;cursor-=timedelta(days=1)
        completed=conn.execute('''SELECT count(*) FROM (SELECT s.lesson FROM sentences s LEFT JOIN sentence_progress p
            ON p.sentence_id=s.id AND p.profile_id=? GROUP BY s.lesson HAVING count(*)=sum(CASE WHEN p.last_rating IS NOT NULL THEN 1 ELSE 0 END))''',(pid,)).fetchone()[0]
        today_data=days.get(today.isoformat(),{})
        return {**dict(learned),'total':conn.execute('SELECT count(*) FROM sentences').fetchone()[0],
                'daily_goal':goal(conn,pid),'today_new':today_data.get('new_sentences',0),
                'today_sentences':today_data.get('sentences',0),'today_reviews':today_data.get('reviews',0),
                'streak':streak,'completed_lessons':completed,
                'modes':[dict(r) for r in conn.execute('SELECT mode,count(*) total FROM sentence_events WHERE profile_id=? GROUP BY mode',(pid,))],
                'activity':[{'day':(today-timedelta(days=i)).isoformat(),**days.get((today-timedelta(days=i)).isoformat(),{'reviews':0,'sentences':0,'new_sentences':0})} for i in range(6,-1,-1)]}

    @app.get('/api/sentences/lessons')
    def lessons(user=Depends(profile),conn=Depends(connection)):
        return [dict(r) for r in conn.execute('''SELECT s.lesson,count(*) total,group_concat(DISTINCT s.level) levels,
           group_concat(DISTINCT s.topic) topics,
           sum(CASE WHEN p.last_rating IS NOT NULL THEN 1 ELSE 0 END) learned,
           sum(CASE WHEN p.due_at<=? THEN 1 ELSE 0 END) due,
           sum(CASE WHEN p.stage>=4 AND p.interval_days>=14 THEN 1 ELSE 0 END) mastered
           FROM sentences s LEFT JOIN sentence_progress p ON p.sentence_id=s.id AND p.profile_id=?
           GROUP BY s.lesson ORDER BY s.lesson''',(clock().isoformat(),user['id']))]

    @app.get('/api/sentences')
    def library(q: str='',topic: str='',level: Literal['','basic','A1','A2','B1','B2','C1']='',context: str='',
                lesson: int | None=Query(default=None,ge=1,le=90),status: Literal['all','new','learned','mastered','saved','due']='all',
                page: int=Query(default=1,ge=1),page_size: int=Query(default=15,ge=1,le=100),
                user=Depends(profile),conn=Depends(connection)):
        sql,args=base_query(),[user['id']]
        filters,values=filter_sql(topic,level,context,lesson);sql+=filters;args+=values
        if q.strip():
            needle=search_key(q.strip()).replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            sql+=" AND s.search_text LIKE ? ESCAPE '\\'";args.append('%'+needle+'%')
        sql+={'all':'','new':' AND p.last_rating IS NULL','learned':' AND p.last_rating IS NOT NULL',
              'mastered':' AND p.stage>=4 AND p.interval_days>=14','saved':' AND p.saved=1','due':' AND p.due_at<=?'}[status]
        if status=='due':args.append(clock().isoformat())
        total=conn.execute('SELECT count(*) FROM ('+sql+')',args).fetchone()[0]
        rows=conn.execute(sql+' ORDER BY s.sort_order LIMIT ? OFFSET ?',args+[page_size,(page-1)*page_size])
        return {'items':[dict(r) for r in rows],'total':total,'page':page,'page_size':page_size}

    @app.get('/api/sentences/queue')
    def queue(mode: Literal['mixed','due','new','saved','lesson','single']='mixed',level: Literal['','basic','A1','A2','B1','B2','C1']='basic',
              topic: str='',lesson: int | None=Query(default=None,ge=1,le=90),limit: int=Query(default=5,ge=5,le=10),sentence_id: str='',
              user=Depends(profile),conn=Depends(connection)):
        pid=user['id'];stamp=clock().isoformat()
        if limit not in {5,10}:raise HTTPException(422,'Mỗi lượt chọn 5 hoặc 10 câu.')
        if mode=='single':
            if not sentence_id:raise HTTPException(422,'Hãy chọn câu cần luyện.')
            return {'items':[row_for(conn,pid,sentence_id)],'due_remaining':0,'new_remaining':None,'daily_goal':goal(conn,pid)}
        filters,values=filter_sql(topic,level,'',lesson)
        sql=base_query()+filters;args=[pid]+values
        if mode=='lesson':
            if lesson is None:raise HTTPException(422,'Hãy chọn buổi học.')
            rows=conn.execute(sql+' ORDER BY CASE WHEN p.last_rating IS NULL THEN 0 ELSE 1 END,s.sort_order LIMIT ?',args+[limit]).fetchall()
            return {'items':[dict(r) for r in rows],'due_remaining':0,'new_remaining':None,'daily_goal':goal(conn,pid)}
        if mode=='saved':
            rows=conn.execute(sql+' AND p.saved=1 ORDER BY s.sort_order LIMIT ?',args+[limit]).fetchall()
            return {'items':[dict(r) for r in rows],'due_remaining':0,'new_remaining':None,'daily_goal':goal(conn,pid)}
        due_count=conn.execute('SELECT count(*) FROM ('+sql+' AND p.due_at<=?)',args+[stamp]).fetchone()[0]
        due_rows=conn.execute(sql+' AND p.due_at<=? ORDER BY p.due_at,s.sort_order LIMIT 20',args+[stamp]).fetchall() if mode!='new' else []
        new_today=conn.execute('SELECT count(*) FROM sentence_events WHERE profile_id=? AND day=? AND is_new=1',(pid,clock().date().isoformat())).fetchone()[0]
        remaining=max(0,goal(conn,pid)-new_today)
        slots=0 if mode=='due' or due_count>=20 else min(remaining,limit,20-len(due_rows))
        new_rows=conn.execute(sql+' AND p.last_rating IS NULL ORDER BY s.sort_order LIMIT ?',args+[slots]).fetchall() if slots else []
        return {'items':[dict(r) for r in [*due_rows,*new_rows]],'due_remaining':max(0,due_count-len(due_rows)),
                'new_remaining':remaining,'daily_goal':goal(conn,pid)}

    @app.put('/api/sentences/{sentence_id}/note')
    def note(sentence_id: str,body: SentenceNote,user=Depends(profile),conn=Depends(connection)):
        row_for(conn,user['id'],sentence_id)
        conn.execute('INSERT OR IGNORE INTO sentence_progress(profile_id,sentence_id) VALUES(?,?)',(user['id'],sentence_id))
        if body.saved is not None:
            conn.execute('UPDATE sentence_progress SET saved=? WHERE profile_id=? AND sentence_id=?',(int(body.saved),user['id'],sentence_id))
        if body.note is not None:
            conn.execute('UPDATE sentence_progress SET note=? WHERE profile_id=? AND sentence_id=?',(body.note.strip(),user['id'],sentence_id))
        return row_for(conn,user['id'],sentence_id)

    @app.post('/api/sentences/review')
    def review(body: SentenceReview,user=Depends(profile),conn=Depends(connection)):
        pid=user['id'];conn.execute('BEGIN IMMEDIATE')
        current=row_for(conn,pid,body.sentence_id)
        previous=conn.execute('SELECT * FROM sentence_events WHERE id=?',(body.event_id,)).fetchone()
        if previous:
            if any(previous[key]!=value for key,value in [('profile_id',pid),('sentence_id',body.sentence_id),('rating',body.rating),('mode',body.mode)]):
                raise HTTPException(409,'Mã lượt học này đã được dùng cho thao tác khác.')
            return current
        stage=current['stage'];interval=current['interval_days']
        if body.rating=='again':
            stage,interval=0,0;due=clock()+timedelta(minutes=10)
        else:
            if body.rating=='hard':
                interval=max(1,interval//2)
            else:
                stage=min(7,stage+(2 if body.rating=='easy' else 1))
                interval=[1,3,7,14,30,60,120][max(0,stage-1)]
            due=clock()+timedelta(days=interval)
        conn.execute('''INSERT INTO sentence_progress(profile_id,sentence_id,stage,interval_days,due_at,last_rating)
          VALUES(?,?,?,?,?,?) ON CONFLICT(profile_id,sentence_id) DO UPDATE SET stage=excluded.stage,
          interval_days=excluded.interval_days,due_at=excluded.due_at,last_rating=excluded.last_rating''',
          (pid,body.sentence_id,stage,interval,due.isoformat(),body.rating))
        stamp=clock()
        conn.execute('INSERT INTO sentence_events VALUES(?,?,?,?,?,?,?,?)',
                     (body.event_id,pid,body.sentence_id,body.mode,body.rating,int(current['last_rating'] is None),stamp.isoformat(),stamp.date().isoformat()))
        return row_for(conn,pid,body.sentence_id)
