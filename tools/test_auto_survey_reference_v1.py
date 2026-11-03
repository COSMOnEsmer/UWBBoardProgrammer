"""Capture one real stationary Tag reference, with optional partial continuation."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import threading
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v8'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.ble_controller import run_ble
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import capture_reference

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True)
    parser.add_argument('--point',type=float,nargs=3,required=True);parser.add_argument('--previous',type=Path)
    args=parser.parse_args()
    previous=json.loads(args.previous.read_text(encoding='utf8')) if args.previous else None
    folder=ROOT/'verification'/('auto-survey-reference-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:
        value=run_ble(capture_reference(Profile.for_mode('tdoa_4'),None,args.port,args.serial,
                      lambda line:print(line,flush=True),threading.Event(),lambda kind,data:save_new(folder,kind,data),
                      previous=previous,known_position=args.point))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    report=folder/'report.json';report.write_text(json.dumps(value,indent=2),encoding='utf8')
    print(json.dumps(dict(report=str(report),complete=value.get('complete'),missing=value.get('missing'),
                         ranges=value.get('ranges'),errors=value.get('errors'),error=value.get('error'))),flush=True)
