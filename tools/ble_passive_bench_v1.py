"""Check BLE reception without retaining names/addresses or connecting."""
import asyncio,json,sys
from datetime import datetime,timezone
from pathlib import Path
sys.coinit_flags=0
from bleak import BleakScanner
ROOT=Path(__file__).resolve().parents[1]
async def main():
    report={'created_utc':datetime.now(timezone.utc).isoformat(),'scan_mode':'passive','duration_s':8,'advertisements':0,'connections_attempted':False,'peer_names_or_addresses_saved':False}
    def received(device,advertisement):report['advertisements']+=1
    try:
        async with BleakScanner(received,scanning_mode='passive'):await asyncio.sleep(8)
        report['scan_completed']=True
    except Exception as e:report['scan_completed']=False;report['error']=repr(e)
    folder=ROOT/'verification'/('ble-bench-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir(exist_ok=False)
    with (folder/'passive-scan.v1.json').open('x',encoding='utf8') as out:json.dump(report,out,indent=2)
    print(json.dumps({'report':str(folder/'passive-scan.v1.json'),**report}))
asyncio.run(main())
