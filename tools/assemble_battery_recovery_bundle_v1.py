"""Retain six earlier images and copy the actually flashed 1.5.1 Tag into a new bundle."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app/revisions/v11'))
from uwb_board_programmer.standalone_flashing import latest_bundle,validate_image
if __name__=='__main__':
    _,previous=latest_bundle(ROOT)
    if len(previous)!=7:raise ValueError('Expected previous seven-image bundle')
    manifest=ROOT/'firmware/releases/_experimental/20261104T015831984530Z/bundle-manifest.json'
    entry=json.loads(manifest.read_text())['images'][0]
    if entry['sha256']!='78b038e539d9e9f3bcc9d20af0ddc6def8a4b2b310cf921b8ed15c22c4de3d51':raise ValueError('Wrong Tag candidate')
    flash=json.loads((ROOT/'verification/flash-jobs/20261104T015935512291Z/report.json').read_text())
    if not flash['program_verify_passed'] or not flash['configuration_acknowledged'] or Path(flash['image'])!=validate_image(ROOT,entry):
        raise ValueError('Flash acceptance mismatch')
    entry.update(eligible_for_default_bundle=True,rf_on_cr2032_observed=True,battery_runtime_validated=False,
                 hardware_validation_scope='Flash/GATT/HPD recovery and Anchor-first DS-TWR on CR2032 with A1-A4, including repeated A4. Current/lifetime and four-reference 3D survey remain unverified.')
    values=[dict(v) for v in previous if v['image_label']!='tag_ble_calibration']+[entry]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=ROOT/'firmware/releases/_experimental'/stamp;folder.mkdir()
    for value in values:
        source=validate_image(ROOT,value);target=folder/value['image_label']/source.name;target.parent.mkdir()
        shutil.copy2(source,target);value['file']=target.relative_to(ROOT).as_posix()
        value.pop('source_work',None);value.pop('size_output',None);validate_image(ROOT,value)
    output=folder/'bundle-manifest.json'
    with output.open('x',encoding='utf8') as out:json.dump(dict(schema=1,created_utc=stamp,images=values,application='2.3.1',
                     battery_calibration_pilot=True,full_3d_hardware_validated=False),out,indent=2)
    assert latest_bundle(ROOT)[0]==output
    print(json.dumps(dict(manifest=str(output),images=len(values))))
