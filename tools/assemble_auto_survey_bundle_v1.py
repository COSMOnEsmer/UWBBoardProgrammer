"""Freeze the tested mixed-version images into a NEW complete six-image bundle."""
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v8')]
from uwb_board_programmer.standalone_flashing import latest_bundle,validate_image

def main():
    previous,old=latest_bundle(ROOT)
    sources=[('20261103T195209791180Z',('master','slave2')),
             ('20261103T200947324440Z',('slave3','slave4')),
             ('20261103T202422766557Z',('tag_setup',))]
    entries=[]
    for stamp,labels in sources:
        manifest=ROOT/'firmware/releases/_experimental'/stamp/'bundle-manifest.json'
        values=json.loads(manifest.read_text(encoding='utf8'))['images']
        for label in labels:entries.append(next(dict(value) for value in values if value['image_label']==label))
    entries.append(dict(next(value for value in old if value['image_label']=='tag_battery')))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder=ROOT/'firmware/releases/_experimental'/stamp;folder.mkdir(exist_ok=False)
    for entry in entries:
        source=validate_image(ROOT,entry)
        target=folder/entry['image_label']/source.name;target.parent.mkdir()
        shutil.copy2(source,target);entry['file']=target.relative_to(ROOT).as_posix()
        entry.pop('source_work',None);entry.pop('size_output',None)
        entry['hardware_validation_scope']='Flash/boot verified on Rev4.1; selected TWR links tested. Full survey and 3D accuracy not yet validated.'
        validate_image(ROOT,entry)
    output=folder/'bundle-manifest.json'
    with output.open('x',encoding='utf8') as stream:
        json.dump(dict(schema=1,created_utc=stamp,images=entries,application='2.2.0',
                       calibration_method='four known non-coplanar Tag reference points; USB Tag; sequential anchor power supported',
                       normal_tag_battery_firmware_preserved=True,full_3d_hardware_validated=False),stream,indent=2)
    selected,_=latest_bundle(ROOT)
    assert selected==output
    print(json.dumps(dict(manifest=str(output),images=[dict(label=e['image_label'],version=e['version'],sha256=e['sha256']) for e in entries])))

if __name__=='__main__':main()
