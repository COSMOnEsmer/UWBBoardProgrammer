"""Exercise the new 2.2.1 GUI acquisition backend on real powered subsets."""
from datetime import datetime,timezone
import argparse
import json
from pathlib import Path
import sys
import threading
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v9'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.ble_controller import run_ble
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import capture_reference

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True)
    parser.add_argument('--seconds',type=int,default=20);args=parser.parse_args()
    folder=ROOT/'verification'/('auto-survey-app-2.2.1-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:
        value=run_ble(capture_reference(Profile.for_mode('tdoa_4'),None,args.port,args.serial,
                      lambda line:print(line,flush=True),threading.Event(),lambda kind,data:save_new(folder,kind,data),
                      known_position=[0.,0.,0.],capture_seconds=args.seconds))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    value.update(capture_purpose='link-diagnostics-only',survey_geometry_verified=False,previous_ranges_reused=False)
    report=folder/'report.json'
    with report.open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(report),ranges=value.get('ranges'),quality=value.get('quality'),missing=value.get('missing'),errors=value.get('errors'),error=value.get('error'))),flush=True)
