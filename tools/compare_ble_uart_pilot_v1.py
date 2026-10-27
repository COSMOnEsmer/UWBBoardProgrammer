"""Compare real decoded BLE records to simultaneous UART records by RF identity."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FIELDS=('boot','peer_mac','frame_type','frame_number','status','message_control',
        'timestamp_bits','tx_timestamp_bits','rx_timestamp_hex','tx_timestamp_hex',
        'az_fom','el_fom','nlos')


def compare(ble, uart):
    def key(row):return row['boot'],row['peer_mac'],row['rx_timestamp_hex']
    index={key(row):row for row in uart if row.get('kind')=='rx'}
    matched=0;unmatched=0;differences=[]
    for row in ble:
        reference=index.get(key(row))
        if reference is None:unmatched+=1;continue
        matched+=1
        wrong={field:[reference.get(field),row.get(field)] for field in FIELDS
               if reference.get(field)!=row.get(field)}
        for field in ('azimuth_deg','elevation_deg'):
            # Wire decoder maps the documented invalid angle sentinels to None.
            value=reference[field]
            if abs(value-32767/128)<1e-6 or abs(value+256)<1e-6:value=None
            if (value is None)!=(row[field] is None) or (value is not None and abs(value-row[field])>1e-6):
                wrong[field]=[value,row[field]]
        if wrong:differences.append(dict(rf_identity=key(row),fields=wrong))
    return dict(ble_records=len(ble),uart_records=len(index),matched_records=matched,
                ble_outside_uart_capture=unmatched,mismatches=differences,
                passed=matched>0 and not differences,
                timestamp_comparison='original integer hex, no floating-point timestamps')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ble-events',required=True,type=Path)
    parser.add_argument('--uart-records',required=True,type=Path)
    args=parser.parse_args()
    events=[json.loads(line) for line in args.ble_events.read_text(encoding='utf8').splitlines()]
    ble=[row['data'] for row in events if row.get('kind')=='observation']
    uart=[json.loads(line) for line in args.uart_records.read_text(encoding='utf8').splitlines()]
    result=compare(ble,uart)
    path=ROOT/'verification'/('ble-uart-comparison-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    with path.open('x',encoding='utf8') as output:json.dump(result,output,indent=2)
    print(json.dumps(dict(report=str(path),**result)))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
