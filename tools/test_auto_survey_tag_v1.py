"""Real A1/Type2DK TWR test with the Tag controlled over its USB console."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import statistics
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v8'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.ble_controller import run_ble
from uwb_board_programmer.ble_transport import Binding
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_tag import UsbSurveyTag

async def capture(port,usb_serial):
    tag=UsbSurveyTag(port,usb_serial,'0200000000000101')
    await asyncio.to_thread(tag.open)
    try:
        async with SurveyNetwork([Binding('A1','0200000000000001','master')],lambda text:print(text,flush=True)) as network:
            result=await network.measure_tag('A1',tag,5)
            restored=network.last_restore_acknowledged
        return dict(tag_hello=tag.hello,pair=result,restore_acknowledged=restored,simulated=False)
    finally:tag.close()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True);args=parser.parse_args()
    folder=ROOT/'verification'/('auto-survey-real-tag-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir(exist_ok=False)
    try:report=run_ble(capture(args.port,args.serial))
    except Exception as error:report={'error':type(error).__name__+': '+str(error),'simulated':False}
    (folder/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    distances=[value['distance_m'] for value in report.get('pair',{}).get('records',[]) if value['status']==0 and not value['nlos']]
    print(json.dumps({'report':str(folder/'report.json'),'LOS_samples':len(distances),
                     'median_m':statistics.median(distances) if distances else None,
                     'restore_acknowledged':report.get('restore_acknowledged'),'error':report.get('error')},indent=2),flush=True)
    if report.get('error') or not distances:raise SystemExit(1)

if __name__=='__main__':main()
