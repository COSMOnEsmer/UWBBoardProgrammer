"""Copy the existing six images plus the actually tested BLE Tag into NEW output."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v10')]
from uwb_board_programmer.standalone_flashing import latest_bundle,validate_image
if __name__=='__main__':
    _,previous=latest_bundle(ROOT)
    if len(previous)!=6:raise ValueError('Expected the previous complete six-image bundle')
    pilot=ROOT/'firmware/releases/_experimental/20261104T004732101740Z/bundle-manifest.json'
    entry=json.loads(pilot.read_text())['images'][0]
    if entry['sha256']!='455457c12f5f15fd0bec2e6c9850738e3d22cd985d628a06adbbe386438ae8da':raise ValueError('Wrong tested Tag binary')
    entry.update(eligible_for_default_bundle=True,rf_on_cr2032_observed=True,
                 battery_runtime_validated=False,hardware_validation_scope='Flash/GATT/DS-TWR on CR2032 with A1 and A2. Current, lifetime and full survey accuracy remain unverified.')
    values=[dict(value) for value in previous]+[entry]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=ROOT/'firmware/releases/_experimental'/stamp;folder.mkdir()
    for value in values:
        source=validate_image(ROOT,value);target=folder/value['image_label']/source.name;target.parent.mkdir()
        shutil.copy2(source,target);value['file']=target.relative_to(ROOT).as_posix()
        value.pop('source_work',None);value.pop('size_output',None);validate_image(ROOT,value)
    manifest=folder/'bundle-manifest.json'
    with manifest.open('x',encoding='utf8') as output:json.dump(dict(schema=1,created_utc=stamp,images=values,application='2.3.0',
                         battery_calibration_pilot=True,full_3d_hardware_validated=False),output,indent=2)
    assert latest_bundle(ROOT)[0]==manifest
    print(json.dumps(dict(manifest=str(manifest),images=len(values))))
