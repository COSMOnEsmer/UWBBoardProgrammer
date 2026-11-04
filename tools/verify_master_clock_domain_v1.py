"""Replay recorded RF with original receipt timing; never publish replay fixes."""
import argparse,importlib.util,json,sys,time
from pathlib import Path
from datetime import datetime,timedelta,timezone
from collections import Counter
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v17'),str(ROOT/'app/battery_calibration/v2'),str(ROOT/'app/ble_prototype/v1')]
from uwb_board_programmer.models import Profile,Observation
from uwb_board_programmer.engine import Pipeline
from uwb_board_programmer.clock_recovery import InterpolatedClockFit,AwaitingSync

def main():
    parser=argparse.ArgumentParser();parser.add_argument('session',type=Path);parser.add_argument('--seconds',type=int,default=120);parser.add_argument('--end');args=parser.parse_args()
    rows=[]
    for line in args.session.open(encoding='utf8'):
        try:rows.append(json.loads(line))
        except ValueError:pass
    profile=Profile.from_dict(rows[0]['data']['profile']);end=datetime.fromisoformat((args.end or rows[-1]['recorded_utc']).replace('Z','+00:00'));start=end-timedelta(seconds=args.seconds)
    events=[r for r in rows if r['kind'] in ('observation','reset') and start<=datetime.fromisoformat(r['recorded_utc'].replace('Z','+00:00'))<=end]
    spec=importlib.util.spec_from_file_location('uwb_board_programmer.clock_before',ROOT/'app/revisions/v16/uwb_board_programmer/clock_recovery.py');before=importlib.util.module_from_spec(spec);spec.loader.exec_module(before);before.AwaitingSync=AwaitingSync
    results={}
    for name,clock_type in [('before_2_8_0',before.InterpolatedClockFit),('master_domain_fix',InterpolatedClockFit)]:
        rejects=Counter();fixes=[];samples=Counter();ready=Counter();sim=[0.]
        with patch.object(time,'monotonic',lambda:sim[0]):
            pipe=Pipeline(profile,record=lambda k,d:rejects.update([d['reason']]) if k=='rejected' else None,fix=fixes.append,allow_history=True)
            pipe.continuous_display=False;pipe.clock_factory=clock_type;pipe.clocks={a.id:clock_type() for a in profile.anchors if a.role=='slave'}
            for row in events:
                sim[0]=(datetime.fromisoformat(row['recorded_utc'].replace('Z','+00:00'))-start).total_seconds()
                if row['kind']=='reset':pipe.reset(row['data']['anchor_id']);continue
                o=Observation(**row['data'])
                try:pipe.accept(o)
                except ValueError:pass
                if o.frame_type=='SYNC' and o.anchor_id in pipe.clocks:
                    samples[o.anchor_id]+=1;ready[o.anchor_id]+=pipe.clocks[o.anchor_id].ready()
            results[name]=dict(accepted_fixes=len(fixes),solver_attempts=pipe.solver_attempts,rejections=dict(rejects),clock_ready_fraction={a:ready[a]/samples[a] for a in samples},last_fixes=[{k:v for k,v in f.items() if k in ('x_m','y_m','z_m','accuracy_m','z_uncertainty_m','time')} for f in fixes[-3:]])
    report=dict(window_start=start.isoformat(),window_end=end.isoformat(),receipt_timing_preserved=True,replay_only=True,cloud_publication=False,results=results)
    output=ROOT/'verification'/('master-clock-domain-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    with output.open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
    print(json.dumps(dict(report=str(output),**report),indent=2))

if __name__=='__main__':main()
