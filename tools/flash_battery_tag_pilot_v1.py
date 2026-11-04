"""Flash only an identified Type2DK with an explicit experimental manifest."""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v9'),str(ROOT/'app/ble_prototype/v1')]
from uwb_board_programmer.survey_workflow import identify_usb_board
from uwb_board_programmer.standalone_flashing import validate_image,flash_selected

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',required=True);parser.add_argument('--serial',required=True)
    parser.add_argument('--manifest',type=Path,required=True);args=parser.parse_args()
    manifest=args.manifest.resolve()
    if not manifest.is_relative_to(ROOT/'firmware/releases/_experimental'):raise ValueError('Experimental manifest must remain in this workspace')
    entries=json.loads(manifest.read_text(encoding='utf8'))['images']
    if len(entries)!=1:raise ValueError('Expected the explicit one-image Tag pilot manifest')
    entry=entries[0]
    if (entry.get('model')!='Type2DK' or entry.get('version')!='1.5.0-pilot' or
        entry.get('image_label')!='tag_ble_calibration' or entry.get('provisioned_mac')!='0200000000000101' or
        entry.get('battery_calibration') is not True or entry.get('eligible_for_default_bundle') is not False):
        raise ValueError('Wrong image type; refusing to Flash')
    validate_image(ROOT,entry)
    hello=identify_usb_board(ROOT,args.port,args.serial);print(json.dumps(dict(identified=hello)),flush=True)
    if hello.get('model')!='Type2DK' or hello.get('role')!='tag' or hello.get('mac')!=entry['provisioned_mac']:
        raise ValueError('Connected board is not the commissioned Type2DK Tag; no Flash was written')
    result=flash_selected(ROOT,entry,args.port,args.serial,lambda value:print(value,flush=True))
    print(json.dumps(result),flush=True)
    if not result.get('program_verify_passed') or not result.get('configuration_acknowledged'):raise SystemExit(1)
