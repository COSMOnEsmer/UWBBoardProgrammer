"""Range-only survey geometry with explicit origin, plane and reflection checks.

Distances determine relative geometry; they do not determine geographic axes or
jointly calibrate unknown antenna delays. Independent distance checks are kept
separate from the fit residual and are required by the UI before profile acceptance.
"""
from itertools import combinations
import math
import numpy as np
from scipy.optimize import least_squares


def estimate_range(records,min_samples=12):
    usable=[float(r['distance_m']) for r in records if r.get('status')==0 and
            r.get('nlos') is False and math.isfinite(r.get('distance_m',float('nan'))) and
            .05<=r['distance_m']<=50]
    if len(usable)<min_samples:raise ValueError('Need at least 12 successful LOS range samples')
    values=np.array(usable);median=float(np.median(values))
    mad=float(1.4826*np.median(np.abs(values-median)))
    retained=values[np.abs(values-median)<=max(.03,3*mad)]
    if len(retained)<min_samples:raise ValueError('Too many inconsistent range samples')
    spread=float(np.std(retained,ddof=1))
    if spread>.20:raise ValueError('Range samples are unstable; check LOS and placement')
    return dict(distance_m=float(np.median(retained)),sample_std_m=spread,
                # Keep a systematic floor; averaging cannot remove fixed bias.
                model_sigma_m=math.hypot(.05,spread/math.sqrt(len(retained))),
                samples=len(retained),discarded=len(records)-len(retained))


def _edge(a,b):return tuple(sorted((a,b)))


def recover_anchors(ids,edges):
    if len(ids)!=4 or len(set(ids))!=4:raise ValueError('Auto Survey needs four distinct anchors')
    missing=[_edge(a,b) for a,b in combinations(ids,2) if _edge(a,b) not in edges]
    if missing:raise ValueError('Missing anchor-pair ranges: '+str(missing))
    distances=np.zeros((4,4))
    for i,j in combinations(range(4),2):
        value=float(edges[_edge(ids[i],ids[j])]['distance_m'])
        if not math.isfinite(value) or not .05<=value<=50:raise ValueError('Invalid anchor distance')
        distances[i,j]=distances[j,i]=value
    for i,j,k in combinations(range(4),3):
        sides=sorted((distances[i,j],distances[i,k],distances[j,k]))
        if sides[0]+sides[1]<=sides[2]:raise ValueError('Range graph violates a triangle inequality')
    centering=np.eye(4)-np.ones((4,4))/4
    gram=-.5*centering@(distances**2)@centering
    eigenvalues,eigenvectors=np.linalg.eigh(gram)
    order=np.argsort(eigenvalues)[::-1];values=eigenvalues[order[:3]]
    if values[0]<=0 or values[2]<=max(1e-6,values[0]*1e-4):
        raise ValueError('Range graph does not constrain non-coplanar 3D anchor geometry')
    noise=max(float(value.get('model_sigma_m',.05)) for value in edges.values())
    if math.sqrt(values[2])<3*noise:
        raise ValueError('Vertical anchor separation is too small compared with range uncertainty')
    xyz=eigenvectors[:,order[:3]]*np.sqrt(values)
    residual=max(abs(np.linalg.norm(xyz[i]-xyz[j])-distances[i,j]) for i,j in combinations(range(4),2))
    if residual>.05:raise ValueError('Range graph is not a consistent 3D geometry')
    return dict(anchors={aid:xyz[i].tolist() for i,aid in enumerate(ids)},
                frame='unoriented relative coordinates',range_residual_m=float(residual),
                geometry_condition=float(math.sqrt(values[0]/values[2])),independent_accuracy_verified=False)


def locate_reference(anchors,ranges):
    ids=list(anchors)
    if len(ids)!=4 or set(ranges)!=set(ids):raise ValueError('Need Tag ranges to all four anchors')
    positions=np.array([anchors[aid] for aid in ids],float)
    distances=np.array([ranges[aid]['distance_m'] for aid in ids],float)
    sigmas=np.array([ranges[aid].get('model_sigma_m',.05) for aid in ids],float)
    if not np.all(np.isfinite(distances)) or np.any(distances<=0) or np.any(sigmas<=0):raise ValueError('Invalid Tag reference ranges')
    matrix=2*(positions[1:]-positions[0])
    if np.linalg.matrix_rank(matrix)<3 or np.linalg.cond(matrix)>1e4:raise ValueError('Tag reference geometry is poorly conditioned')
    rhs=np.sum(positions[1:]**2,axis=1)-np.dot(positions[0],positions[0])-distances[1:]**2+distances[0]**2
    initial=np.linalg.solve(matrix,rhs)
    def residual(x):return (np.linalg.norm(x-positions,axis=1)-distances)/sigmas
    starts=[initial,positions.mean(axis=0)]
    candidates=[least_squares(residual,start,loss='huber',f_scale=1.5,max_nfev=200) for start in starts]
    candidates=[fit for fit in candidates if fit.success]
    if not candidates:raise ValueError('Reference point solve did not converge')
    candidates.sort(key=lambda fit:float(np.dot(residual(fit.x),residual(fit.x))));best=candidates[0]
    if np.linalg.matrix_rank(best.jac)<3 or np.linalg.cond(best.jac)>1e4:raise ValueError('Reference point is poorly conditioned')
    raw=np.linalg.norm(best.x-positions,axis=1)-distances
    if max(abs(raw))>.15 or np.sqrt(np.mean(residual(best.x)**2))>3:raise ValueError('Reference ranges disagree with the anchor geometry')
    for other in candidates[1:]:
        if np.linalg.norm(other.x-best.x)>.3 and np.dot(residual(other.x),residual(other.x))-np.dot(residual(best.x),residual(best.x))<1:
            raise ValueError('Reference point is ambiguous')
    covariance=np.linalg.inv(best.jac.T@best.jac)*max(1,float(np.mean(residual(best.x)**2)))
    return dict(position=best.x.tolist(),residual_m=float(np.sqrt(np.mean(raw**2))),
                model_std_m=np.sqrt(np.maximum(0,np.diag(covariance))).tolist())


def solve_reference_survey(anchor_ids,references):
    names=('origin','x','y','z')
    if set(references)!=set(names):raise ValueError('Capture all four measured reference points')
    points={name:references[name].get('known_position') for name in names}
    if any(value is None or len(value)!=3 for value in points.values()):raise ValueError('Measured reference XYZ is required')
    xyz=np.asarray(list(points.values()),float)
    if not np.all(np.isfinite(xyz)) or np.linalg.matrix_rank(xyz[1:]-xyz[0])<3:
        raise ValueError('Reference points must constrain three dimensions')
    solved={}
    for aid in anchor_ids:
        if any(aid not in references[name].get('ranges',{}) for name in names):raise ValueError('Missing reference ranges for '+aid)
        solved[aid]=locate_reference(points,{name:references[name]['ranges'][aid] for name in names})
    return dict(anchors={aid:value['position'] for aid,value in solved.items()},
                anchor_quality=solved,reference_positions=points,origin=points['origin'],
                z_meaning='height relative to the measured Tag origin',
                method='four known non-coplanar Tag reference points / TWR',
                independent_accuracy_verified=False)


def register_frame(anchors,references,above_anchor):
    if set(references)!={'origin','x','y'}:raise ValueError('Capture origin and two plane reference points')
    if above_anchor not in anchors:raise ValueError('Select an anchor physically above the reference plane')
    origin=np.asarray(references['origin']['position'],float)
    vx=np.asarray(references['x']['position'],float)-origin
    vy=np.asarray(references['y']['position'],float)-origin
    lx,ly=np.linalg.norm(vx),np.linalg.norm(vy)
    if min(lx,ly)<.4:raise ValueError('Reference movements must be at least 0.4 m')
    cosine=float(np.dot(vx,vy)/(lx*ly))
    if abs(cosine)>.866:raise ValueError('Plane reference directions are too nearly collinear')
    x=vx/lx;y=vy-np.dot(vy,x)*x;y/=np.linalg.norm(y);z=np.cross(x,y)
    height=float(np.dot(np.asarray(anchors[above_anchor])-origin,z))
    if abs(height)<.15:raise ValueError('Selected above-plane anchor is too close to the reference plane')
    if height<0:z=-z  # Resolve the range-only reflection with a physical constraint.
    rotation=np.vstack((x,y,z))
    transformed={aid:(rotation@(np.asarray(value)-origin)).tolist() for aid,value in anchors.items()}
    poses={name:(rotation@(np.asarray(value['position'])-origin)).tolist() for name,value in references.items()}
    return dict(anchors=transformed,references=poses,above_anchor=above_anchor,
                origin=[0.,0.,0.],rotation=rotation.tolist(),reference_distances_m={'x':float(lx),'y':float(ly)},
                z_meaning='height relative to the Tag reference plane',independent_accuracy_verified=False)


def check_reference_distances(result,measured_x,measured_y,tolerance=.15):
    if not all(math.isfinite(v) and v>=.4 for v in (measured_x,measured_y)):raise ValueError('Enter independent measured reference distances in metres')
    errors={name:result['reference_distances_m'][name]-value for name,value in [('x',measured_x),('y',measured_y)]}
    if any(abs(value)>tolerance for value in errors.values()):raise ValueError('Independent distance check failed: '+str(errors))
    return dict(errors_m=errors,tolerance_m=tolerance,passed=True,
                limitation='Checks these baselines only; further holdout Tag positions/heights are required for TDoA accuracy validation.')
