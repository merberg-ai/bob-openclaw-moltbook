"""Original post drafts and publishing state. No network or secret access here."""
from __future__ import annotations
import hashlib, re, secrets
from datetime import datetime, timezone
from bob_publish_common import now, event

IDENT = re.compile(r'^[0-9a-f]{24}$')
SUBMOLTS = ('general', 'introductions')

def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS original_requests (
      id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('intro','thought')),
      state TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT, error TEXT)''')
    db.execute('''CREATE TABLE IF NOT EXISTS original_posts (
      id TEXT PRIMARY KEY, request_id TEXT UNIQUE, submolt TEXT NOT NULL,
      title TEXT NOT NULL, content TEXT NOT NULL, digest TEXT NOT NULL,
      state TEXT NOT NULL, source TEXT NOT NULL, created_at TEXT NOT NULL,
      approved_at TEXT, queued_at TEXT, attempted_at TEXT, updated_at TEXT NOT NULL,
      post_id TEXT, challenge_code TEXT, challenge_text TEXT,
      challenge_expires_at TEXT, verify_answer TEXT, last_error TEXT,
      visible_checked_at TEXT, visible INTEGER NOT NULL DEFAULT 0)''')
    db.execute('CREATE INDEX IF NOT EXISTS originals_state_idx ON original_posts(state, created_at)')
    db.execute('''CREATE TABLE IF NOT EXISTS original_post_replies (
      id TEXT PRIMARY KEY, post_id TEXT NOT NULL, parent_id TEXT,
      author TEXT, content TEXT, detected_at TEXT NOT NULL)''')

def digest(submolt,title,content):
    return hashlib.sha256((submolt+'\n'+title+'\n'+content).encode('utf8')).hexdigest()

def validate(submolt,title,body):
    if submolt not in SUBMOLTS: raise ValueError('Unsupported community')
    if not isinstance(title,str) or not 6 <= len(title.strip()) <= 160 or '\n' in title: raise ValueError('Title must be 6-160 characters, one line')
    if not isinstance(body,str) or not 80 <= len(body.strip()) <= 3500: raise ValueError('Body must be 80-3500 characters')
    if '\x00' in title or '\x00' in body: raise ValueError('Invalid text')
    return submolt,title.strip(),body.strip()

def request_draft(db,kind):
    if kind not in ('intro','thought'): raise ValueError('Invalid draft request')
    queued=db.execute("SELECT count(*) FROM original_requests WHERE state IN ('queued','running')").fetchone()[0]
    if queued >= 2: raise ValueError('Two generation requests already pending')
    if kind == 'intro' and db.execute("SELECT 1 FROM original_requests WHERE kind='intro' AND state IN ('queued','running') LIMIT 1").fetchone():
        raise ValueError('Introduction generation already queued')
    rid=secrets.token_hex(12)
    db.execute('INSERT INTO original_requests(id,kind,state,created_at) VALUES(?,?,?,?)',(rid,kind,'queued',now()))
    event(db,'original_draft_requested',f'{kind} request {rid}')
    return rid

def add_draft(db,request_id,title,content,submolt=None,source='bob'):
    if not IDENT.fullmatch(request_id): raise ValueError('Invalid request ID')
    row=db.execute('SELECT kind,state FROM original_requests WHERE id=?',(request_id,)).fetchone()
    if not row or row[1]!='running': raise ValueError('Request not running')
    submolt=submolt or ('introductions' if row[0]=='intro' else 'general')
    submolt,title,content=validate(submolt,title,content)
    rid=secrets.token_hex(12)
    t=now()
    db.execute('INSERT INTO original_posts(id,request_id,submolt,title,content,digest,state,source,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
               (rid,request_id,submolt,title,content,digest(submolt,title,content),'draft',source,t,t))
    db.execute("UPDATE original_requests SET state='completed',completed_at=? WHERE id=?",(t,request_id))
    event(db,'original_draft_ready',f'{rid}: {title[:90]}')
    return rid

def transition(db,rid,operation,expected_digest):
    if not IDENT.fullmatch(rid): raise ValueError('Invalid draft ID')
    row=db.execute('SELECT submolt,title,content,digest,state FROM original_posts WHERE id=?',(rid,)).fetchone()
    if not row: raise ValueError('Draft not found')
    submolt,title,content,actual,state=row
    if actual!=digest(submolt,title,content) or expected_digest!=actual:raise ValueError('Draft changed; reload page')
    allowed={'approve':('draft','approved'),'reject':('draft','rejected'),'publish':('approved','queued')}
    if operation not in allowed:raise ValueError('Unknown action')
    before,after=allowed[operation]
    if state != before:raise ValueError('Draft is not in the correct state')
    t=now()
    if operation=='approve':db.execute('UPDATE original_posts SET state=?,approved_at=?,updated_at=? WHERE id=?',(after,t,t,rid))
    elif operation=='publish':db.execute('UPDATE original_posts SET state=?,queued_at=?,updated_at=? WHERE id=?',(after,t,t,rid))
    else: db.execute('UPDATE original_posts SET state=?,updated_at=? WHERE id=?',(after,t,rid))
    event(db,'original_'+operation, f'{rid} {title[:90]}')


def edit_draft(db,rid,expected_digest,submolt,title,content):
    if not IDENT.fullmatch(rid):raise ValueError('Invalid draft ID')
    row=db.execute('SELECT digest,state FROM original_posts WHERE id=?',(rid,)).fetchone()
    if not row or row[1]!='draft' or row[0]!=expected_digest:
        raise ValueError('Draft changed or is no longer editable')
    submolt,title,content=validate(submolt,title,content)
    db.execute("UPDATE original_posts SET submolt=?,title=?,content=?,digest=?,source='bob + owner edited',updated_at=? WHERE id=?",
               (submolt,title,content,digest(submolt,title,content),now(),rid))
    event(db,'original_edited',f'{rid} owner modified draft before approval')
