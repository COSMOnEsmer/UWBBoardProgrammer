"""Real leased BLE TWR pair test. Identifies both boards before RF commands."""
import argparse
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v8'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.ble_controller import run_ble
from uwb_board_programmer.ble_transport import Binding
from uwb_board_programmer.survey_transport import SurveyNetwork

async def capture(seconds):
    bindings=[Binding('A1','0200000000000001','master'),Binding('A2','0200000000000002','slave')]
    async with SurveyNetwork(bindings,lambda value:print(value,flush=True)) as network:
        info=dict(network.info)
        pair=await network.measure_pair('A1','A2',seconds)
        restored=await network.restore()
    return dict(board_info=info,pair=pair,restore_acknowledged=restored,simulated=False,cloud_connected=False)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=float,default=6);args=parser.parse_args()
    directory=ROOT/'verification'/('auto-survey-real-pair-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    directory.mkdir(exist_ok=False)
    try:report=run_ble(capture(args.seconds))
    except Exception as error:report={'error':type(error).__name__+': '+str(error),'simulated':False}
    (directory/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(directory/'report.json'),**report},indent=2),flush=True)
    if report.get('error'):raise SystemExit(1)

if __name__=='__main__':main()
