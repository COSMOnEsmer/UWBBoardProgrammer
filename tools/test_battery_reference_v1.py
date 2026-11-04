"""Exercise the 2.3.0 BLE reference backend; no Tag COM, Flash or XYZ fabrication."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import threading
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v10'),str(ROOT/'app/battery_calibration/v1'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.ble_controller import run_ble
from uwb_battery_calibration.capture import capture_reference_ble

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--seconds',type=int,default=20)
    parser.add_argument('--power-source',choices=['unknown','usb','cr2032'],default='unknown');args=parser.parse_args()
    folder=ROOT/'verification'/('battery-reference-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(capture_reference_ble(Profile.for_mode('tdoa_4'),lambda line:print(line,flush=True),threading.Event(),
                      lambda kind,data:save_new(folder,kind,data),known_position=[0.,0.,0.],capture_seconds=args.seconds))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    value.update(power_source_reported=args.power_source,usb_opened=False,survey_geometry_verified=False,capture_purpose='link-diagnostics-only')
    report=folder/'report.json'
    with report.open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(report),complete=value.get('complete'),ranges=value.get('ranges'),quality=value.get('quality'),missing=value.get('missing'),errors=value.get('errors'))),flush=True)
