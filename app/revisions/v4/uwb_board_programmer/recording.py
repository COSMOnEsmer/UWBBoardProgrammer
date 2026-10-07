import json, threading
from pathlib import Path
from .models import unique_path,utc,Profile,Observation
from .engine import Pipeline

class Recorder:
    def __init__(self,root,profile):
        self.path=unique_path(Path(root)/'data/sessions','rf-session','.jsonl');self.lock=threading.Lock()
        self.file=self.path.open('x',encoding='utf-8');self.write('header',{'profile':profile.to_dict(),'mode':'hardware','version':'2.0.1'})
    def write(self,kind,data):
        with self.lock:
            if self.file.closed:return
            self.file.write(json.dumps({'kind':kind,'recorded_utc':utc(),'data':data},ensure_ascii=False,allow_nan=False)+'\n');self.file.flush()
    def close(self):
        with self.lock:self.file.close()

def replay(path,on_fix=lambda *a:None,on_log=lambda *a:None):
    """Replay is deliberately constructed without a cloud publisher or serial port."""
    with open(path,encoding='utf-8') as f:
        first=json.loads(next(f))
        if first.get('kind')!='header':raise ValueError('Missing session header')
        profile=Profile.from_dict(first['data']['profile']);pipe=Pipeline(profile,fix=on_fix,allow_history=True)
        for line in f:
            row=json.loads(line)
            if row['kind']=='reset':pipe.reset(row['data']['anchor_id'])
            elif row['kind']=='observation':
                try:pipe.accept(Observation(**row['data']))
                except ValueError as e:on_log(str(e))
    return pipe.snapshot()
