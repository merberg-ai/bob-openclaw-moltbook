"""Bob v0.5 publication queue: shared integrity checks and database schema.

This module NEVER loads Moltbook credentials, never sends HTTP and never
executes agent-generated text. Public writes live in publisher process only.
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
from contextlib import contextmanager

DATA = Path.home() / '.config' / 'moltbook'
DB = DATA / 'activity-queue.sqlite3'
UUID = re.compile(r'^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$')
RUN_ID = re.compile(r'^\d{8}T\d{6}Z$')

def now():
    return datetime.now(timezone.utc).isoformat()

@contextmanager
def connect():
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    con = sqlite3.connect(DB, timeout=10)
    con.execute('PRAGMA busy_timeout=10000')
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS decisions (run_id TEXT PRIMARY KEY, draft_sha256 TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN (\'approved\',\'rejected\')), decided_at TEXT NOT NULL)')
    con.execute('CREATE TABLE IF NOT EXISTS publish_settings (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
    con.execute('''CREATE TABLE IF NOT EXISTS publish_jobs (
        run_id TEXT PRIMARY KEY, approval_sha256 TEXT NOT NULL, post_id TEXT NOT NULL,
        draft_comment TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode IN ('manual','auto')),
        state TEXT NOT NULL, created_at TEXT NOT NULL, attempted_at TEXT,
        comment_id TEXT, challenge_code TEXT, challenge_text TEXT,
        challenge_expires_at TEXT, verify_answer TEXT, last_error TEXT,
        updated_at TEXT NOT NULL)''')
    con.execute('''CREATE TABLE IF NOT EXISTS published_replies (
        id TEXT PRIMARY KEY, post_id TEXT NOT NULL, comment_id TEXT NOT NULL,
        author TEXT, content TEXT, detected_at TEXT NOT NULL)''')
    con.execute('CREATE TABLE IF NOT EXISTS publish_events (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, kind TEXT NOT NULL, details TEXT NOT NULL)')
    try:
        yield con
        con.commit()
    except BaseException:
        con.rollback()
        raise
    finally:
        con.close()

def setting(db, name, default=''):
    row = db.execute('SELECT value FROM publish_settings WHERE name=?',(name,)).fetchone()
    return row[0] if row else default

def set_setting(db,name,value):
    db.execute('INSERT INTO publish_settings(name,value) VALUES(?,?) ON CONFLICT(name) DO UPDATE SET value=excluded.value',(name,str(value)))

def event(db,kind,details):
    db.execute('INSERT INTO publish_events(at,kind,details) VALUES(?,?,?)',(now(),kind,str(details)[:500]))

def valid_record(obj):
    try:
        rid=obj['run_id']
        if obj.get('schema') != 2 or not isinstance(rid,str) or not RUN_ID.fullmatch(rid): return False
        pid=obj['chosen_post_id']
        if not isinstance(pid,str) or not UUID.fullmatch(pid): return False
        text=obj['draft_comment']
        if not isinstance(text,str) or not text.strip() or len(text)>3000 or len(text.split())>150: return False
        raw= (DATA/f'scout-feed-{rid}.json')
        if obj.get('snapshot_file') != raw.name or not raw.is_file() or raw.stat().st_size>512*1024: return False
        snap = raw.read_bytes()
        if hashlib.sha256(snap).hexdigest() != obj.get('snapshot_sha256'): return False
        feed=json.loads(snap)
        if not isinstance(feed,dict) or not isinstance(feed.get('posts'),list) or not any(isinstance(p,dict) and p.get('id')==pid for p in feed['posts']): return False
        if hashlib.sha256(text.encode()).hexdigest() != obj.get('draft_sha256'): return False
        appr=hashlib.sha256((pid+'\n'+text+'\n'+obj['snapshot_sha256']).encode()).hexdigest()
        return obj.get('approval_sha256')==appr and obj.get('status')=='pending'
    except (KeyError,OSError,TypeError,ValueError):
        return False

def load_record(rid):
    if not isinstance(rid,str) or not RUN_ID.fullmatch(rid): return None
    path= DATA/f'scout-result-{rid}.json'
    try:
        if not path.is_file() or path.stat().st_size>1024*1024: return None
        obj=json.loads(path.read_text(encoding='utf-8'))
        return obj if obj.get('run_id')==rid and valid_record(obj) else None
    except (OSError,ValueError,TypeError,AttributeError): return None

def queue_manual(db, rid):
    obj=load_record(rid)
    if not obj: raise ValueError('Invalid or changed scouting record')
    decision=db.execute('SELECT draft_sha256,status FROM decisions WHERE run_id=?',(rid,)).fetchone()
    if not decision or decision != (obj['approval_sha256'],'approved'):
        raise ValueError('Draft must be explicitly approved and unchanged')
    if db.execute('SELECT 1 FROM publish_jobs WHERE run_id=?',(rid,)).fetchone():
        raise ValueError('Draft already has a publication attempt; no automatic retry')
    db.execute('INSERT INTO publish_jobs(run_id,approval_sha256,post_id,draft_comment,mode,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
               (rid,obj['approval_sha256'],obj['chosen_post_id'],obj['draft_comment'],'manual','queued',now(),now()))
    event(db,'publish_queued',f'{rid} manual publication requested')

def auto_candidates(db, max_count=10):
    if setting(db,'auto_enabled','0') != '1': return 0
    since=setting(db,'auto_since','')
    if not since: return 0
    count=0
    # Restrict to genuinely new records created after opt-in; never post old backlog.
    for p in sorted(DATA.glob('scout-result-*.json')):
        rid=p.name.removeprefix('scout-result-').removesuffix('.json')
        obj=load_record(rid)
        if obj is None: continue
        try:
            created=datetime.strptime(rid,'%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
            if created.isoformat() <= since: continue
        except ValueError: continue
        if db.execute('SELECT 1 FROM decisions WHERE run_id=?',(rid,)).fetchone(): continue
        if db.execute('SELECT 1 FROM publish_jobs WHERE run_id=?',(rid,)).fetchone(): continue
        db.execute('INSERT INTO publish_jobs(run_id,approval_sha256,post_id,draft_comment,mode,state,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',
                   (rid,obj['approval_sha256'],obj['chosen_post_id'],obj['draft_comment'],'auto','queued',now(),now()))
        event(db,'auto_queued',f'{rid} new validated draft queued')
        count+=1
        if count>=max_count: break
    return count
