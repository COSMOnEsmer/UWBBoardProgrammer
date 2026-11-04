"""Create a NEW A4-referenced profile from a saved survey and read-only Edge config.

No credential handling, server mutation, Flash or telemetry publication.
"""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v16'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.coordinates import align_profile,source_profile,floor_geometry
from uwb_board_programmer.cloud import validate_scope

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--profile',type=Path,required=True);parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--anchor-id',default='TP-A4');args=parser.parse_args()
    p=Profile.from_dict(json.loads(args.profile.read_text(encoding='utf8')));cfg=json.loads(args.config.read_text(encoding='utf8'))
    remote=next(a for a in cfg['anchors'] if a['id']==args.anchor_id);floor=next(f for f in cfg['floors'] if f['id']==remote['floorId'])
    if p.alignment:raise ValueError('Use a raw survey input for this commissioning helper')
    p.site_id=cfg['site']['id'];p.floor_id=floor['id'];p.coordinate_frame='survey'
    anchor=next(a for a in p.anchors if a.id==args.anchor_id)
    target=[remote[k] for k in ('posXM','posYM','posZM')];offset=[target[i]-anchor.position[i] for i in range(3)]
    geometry=floor_geometry(floor);geometry['config_version']=cfg.get('configVersion')
    aligned=align_profile(p,0,offset,geometry,True);validate_scope(aligned,cfg)
    aligned.alignment['commissioning']=dict(reference_anchor=anchor.id,server_geometry_compared=True,rf_accuracy_validated=False)
    path=save_new(args.output,'floor-profile',aligned.to_dict())
    print(json.dumps(dict(profile=str(path),frame=aligned.coordinate_frame,offset_m=offset,anchors_compared=len(aligned.anchors),server_coordinates_match=True)))

if __name__=='__main__':main()
