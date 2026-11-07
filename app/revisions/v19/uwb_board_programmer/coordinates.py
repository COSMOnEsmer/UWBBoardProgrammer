"""Explicit metre frames and rigid survey-to-floor registration; no RF synthesis."""
import copy,math
from itertools import product
import numpy as np
from scipy.spatial.transform import Rotation
from .models import Profile,utc

def vector(value):
    a=np.asarray(value,float)
    if a.shape!=(3,) or not np.all(np.isfinite(a)):raise ValueError('Enter three finite coordinates in metres')
    return a

def matrix(yaw):
    if not math.isfinite(float(yaw)):raise ValueError('Enter a finite alignment angle')
    return Rotation.from_euler('z',yaw,degrees=True).as_matrix()

def transform(point,yaw,offset):return (matrix(yaw)@vector(point)+vector(offset)).tolist()

def inverse(point,yaw,offset):return (matrix(yaw).T@(vector(point)-vector(offset))).tolist()

def transform_bounds(bounds,yaw,offset):
    lo,hi=np.asarray(bounds,float)
    corners=np.array([transform(p,yaw,offset) for p in product(*zip(lo,hi))])
    return [corners.min(axis=0).tolist(),corners.max(axis=0).tolist()]

def floor_geometry(remote):
    """Use advertised dimensions; missing lengths require explicit operator entry."""
    return dict(origin_x=float(remote.get('originXM',0)),origin_y=float(remote.get('originYM',0)),
                length=remote.get('lengthM'),width=remote.get('widthM'),height=remote.get('heightM'),
                elevation=float(remote.get('elevationM',0)),level_index=int(remote.get('levelIndex',0)),
                meters_per_pixel=float(remote.get('metersPerPixel',.01)),footprint=remote.get('footprint'),
                name=remote.get('name',''),id=remote.get('id',''))

def floor_bounds(geometry):
    x=float(geometry.get('origin_x',0));y=float(geometry.get('origin_y',0))
    size=vector([geometry.get('length'),geometry.get('width'),geometry.get('height')])
    if np.any(size<=0) or not np.all(np.isfinite([x,y])):raise ValueError('Floor length, width and height must be positive metres')
    return [[x,y,0.],[x+size[0],y+size[1],size[2]]]

def source_profile(profile):
    """Always derive from retained survey data; never accumulate offsets."""
    if profile.alignment or profile.survey_archive:
        if profile.alignment:check_alignment(profile)
        source=Profile.from_dict(copy.deepcopy(profile.alignment['source_profile'] if profile.alignment else profile.survey_archive))
        active={a.mac.upper():a for a in profile.anchors}
        for anchor in source.anchors:
            if anchor.mac.upper() not in active:raise ValueError('Anchor hardware changed; start a new survey')
            row=active[anchor.mac.upper()];anchor.id=row.id;anchor.port=row.port
        source.site_id=profile.site_id;source.floor_id=profile.floor_id;source.tag_id=profile.tag_id
        source.tag_port=profile.tag_port;source.transport=profile.transport
        for key in ('tag_mac','baud','blink_interval_ms','ble_scan_mode','ble_scan_seconds','aoa_sigma_deg','tdoa_sigma_m','min_fom','max_z_uncertainty_m','max_horizontal_uncertainty_m'):
            setattr(source,key,getattr(profile,key))
        return source
    return Profile.from_dict(copy.deepcopy(profile.to_dict()))

def check_alignment(profile):
    if not profile.alignment:return
    a=profile.alignment
    if a.get('site_id')!=profile.site_id or a.get('floor_id')!=profile.floor_id:
        raise ValueError('Alignment belongs to another site/floor. Review alignment again.')
    source={row['mac'].upper():row for row in a['source_profile']['anchors']}
    if set(source)!={row.mac.upper() for row in profile.anchors}:raise ValueError('Alignment hardware mapping changed')
    r=matrix(a['yaw_deg'])
    for row in profile.anchors:
        raw=source[row.mac.upper()]
        if not np.allclose(row.position,transform(raw['position'],a['yaw_deg'],a['translation_m']),atol=1e-7,rtol=0):
            raise ValueError('Aligned coordinates were edited. Restore the saved profile or create a new alignment.')
        original=Rotation.from_euler('xyz',[raw['roll'],raw['pitch'],raw['yaw']],degrees=True).as_matrix()
        if not np.allclose(row.rotation(),r@original,atol=1e-7,rtol=0):raise ValueError('Aligned orientation changed; review alignment')
    if not np.allclose(profile.bounds,floor_bounds(profile.floor_geometry),atol=1e-7,rtol=0):raise ValueError('Floor bounds changed; review alignment')

def require_floor(profile):
    if profile.coordinate_frame!='floor' or not profile.floor_verified:
        raise ValueError('Align survey to floor and confirm the floor coordinate frame before RTLS publishing')
    check_alignment(profile)

def align_profile(profile,yaw,offset,geometry,confirmed=False,references=None):
    source=source_profile(profile);source.alignment={};source.survey_archive={};source.floor_verified=False
    # Source is immutable audit data. Active coordinates, solver, display and cloud
    # all operate directly in F; no additional transform is applied to a solved Tag.
    result=Profile.from_dict(source.to_dict());r=matrix(yaw);offset=vector(offset)
    for anchor in result.anchors:
        anchor.position=transform(anchor.position,yaw,offset)
        angles=Rotation.from_matrix(r@anchor.rotation()).as_euler('xyz',degrees=True)
        anchor.roll,anchor.pitch,anchor.yaw=map(float,angles)
    result.floor_geometry=copy.deepcopy(geometry);result.bounds=floor_bounds(geometry)
    result.survey_archive=source.to_dict()
    result.coordinate_frame='floor';result.floor_verified=bool(confirmed);result.schema_version=2
    result.alignment=dict(schema=1,site_id=result.site_id,floor_id=result.floor_id,
                          yaw_deg=float(yaw),translation_m=offset.tolist(),scale=1.,created_utc=utc(),
                          source_profile=source.to_dict(),references=copy.deepcopy(references or []),
                          source_bounds_in_floor=transform_bounds(source.bounds,yaw,offset),
                          physical_accuracy_validated=False)
    result.name=profile.name+' / Floor aligned' if not profile.name.endswith('/ Floor aligned') else profile.name
    result.validate(require_aoa=False);return result

def fit_references(source,target,max_error=.10):
    """Yaw+translation only, known vertical. Two points identify XY heading."""
    s=np.asarray(source,float);t=np.asarray(target,float)
    if s.shape!=t.shape or s.ndim!=2 or s.shape[1]!=3 or len(s)<2 or not np.all(np.isfinite([s,t])):
        raise ValueError('Enter at least two paired Survey/Floor XYZ points')
    a=s[:,:2]-s[:,:2].mean(axis=0);b=t[:,:2]-t[:,:2].mean(axis=0)
    if np.linalg.norm(a)<.2 or np.linalg.norm(b)<.2:raise ValueError('Reference points must have a useful horizontal separation')
    u,_,vt=np.linalg.svd(a.T@b);d=np.eye(2);d[1,1]=np.linalg.det(vt.T@u.T);r=vt.T@d@u.T
    yaw=math.degrees(math.atan2(r[1,0],r[0,0]));offset=t.mean(axis=0)-matrix(yaw)@s.mean(axis=0)
    errors=np.linalg.norm(s@matrix(yaw).T+offset-t,axis=1)
    if max(errors)>max_error:raise ValueError('Reference fit exceeds tolerance; check scale, heights, axes or reflection')
    return dict(yaw_deg=yaw,translation_m=offset.tolist(),rms_m=float(np.sqrt(np.mean(errors**2))),max_error_m=float(max(errors)))

def outside_floor(profile):
    lo,hi=np.array(profile.bounds,float)
    return [a.id for a in profile.anchors if np.any(vector(a.position)<lo-1e-6) or np.any(vector(a.position)>hi+1e-6)]
