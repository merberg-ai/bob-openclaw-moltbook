"""Credentialed Moltbook API: HTTPS-only, fixed host, no redirects. Worker only."""
from pathlib import Path
from datetime import datetime,timezone
import urllib.request,urllib.error,json,re

BASE='https://www.moltbook.com/api/v1'
CREDENTIALS=Path.home()/'.config/moltbook/credentials.json'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise RuntimeError('Moltbook redirect refused')
OPENER=urllib.request.build_opener(NoRedirect())

def api(method,path,payload=None,*,key=None):
    if not path.startswith('/') or '//' in path:
        raise ValueError('Unexpected API path')
    if '?' in path and not re.fullmatch(r'/posts/[0-9a-fA-F-]{36}/comments\?sort=new&limit=100',path):
        raise ValueError('Unexpected API query')
    headers={'Accept':'application/json','User-Agent':'BobSkullLab/0.6'}
    if key:headers['Authorization']='Bearer '+key
    raw=None
    if payload is not None:
        raw=json.dumps(payload,ensure_ascii=False).encode('utf8')
        headers['Content-Type']='application/json'
    req=urllib.request.Request(BASE+path,raw,headers,method=method)
    try:
        with OPENER.open(req,timeout=15) as r:
            if r.status<200 or r.status>=300:raise RuntimeError('Unexpected HTTP status')
            content=r.read(256*1024+1)
            if len(content)>256*1024:raise RuntimeError('Response too large')
        obj=json.loads(content)
        if not isinstance(obj,dict):raise RuntimeError('Invalid JSON response')
        return obj
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Moltbook HTTP {e.code}') from None

def api_key():
    if CREDENTIALS.stat().st_mode & 0o077:raise RuntimeError('Credentials must be private (0600)')
    key=json.loads(CREDENTIALS.read_text(encoding='utf8')).get('api_key','')
    if not isinstance(key,str) or not key.startswith('moltbook_'):raise RuntimeError('Credentials malformed')
    return key

def parse_time(t):
    try:return datetime.fromisoformat(t.replace('Z','+00:00')).astimezone(timezone.utc)
    except (ValueError,TypeError,AttributeError):return None
