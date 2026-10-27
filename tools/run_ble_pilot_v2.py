"""Use separate Bleak dependencies with the existing desktop Python runtime."""
from pathlib import Path
import runpy
import sys
sys.coinit_flags=0
ROOT=Path(__file__).resolve().parents[1]
dependency=ROOT/'runtime/ble-bench-v2/Lib/site-packages'
if not dependency.is_dir():
    raise SystemExit('Separate BLE runtime missing. See docs/BLE_PILOT_PROTOCOL.v1.md.')
sys.path.insert(0,str(dependency))
targets={'capture':'ble_capture_pilot_v4.py','position':'ble_positioning_pilot_v3.py'}
if len(sys.argv)<2 or sys.argv[1] not in targets:
    raise SystemExit('Usage: run_ble_pilot_v1.py capture|position [options]')
target=ROOT/'tools'/targets[sys.argv.pop(1)]
sys.argv[0]=str(target)
runpy.run_path(str(target),run_name='__main__')
