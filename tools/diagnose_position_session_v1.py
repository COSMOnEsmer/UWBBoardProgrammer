"""Read-only session analysis. Writes a new report; never connects to hardware."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'app/revisions/v6'), str(ROOT/'app/ble_prototype/v1')]
import numpy as np
from uwb_board_programmer.models import Profile, Observation, C_M_S, TICK_S
from uwb_board_programmer.engine import Pipeline
import uwb_board_programmer.positioning as positioning


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('session', type=Path)
    args = parser.parse_args()
    # Freeze one read so a still-running session cannot change this replay.
    rows = []
    for line in args.session.read_text(encoding='utf-8-sig').splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
    profile = Profile.from_dict(rows[0]['data']['profile'])
    events = Counter(row['kind'] for row in rows)
    logged_rejections = Counter(row['data']['reason'] for row in rows if row['kind']=='rejected')
    replay_rejections = Counter()
    observations = Counter()
    clocks = Counter()
    attempts = []
    fixes = []
    now = [0.]
    fitted = []
    original_fit = positioning.least_squares

    def fit(*args, **kwargs):
        result = original_fit(*args, **kwargs)
        if result.success: fitted.append(result)
        return result

    def recorded(kind, data):
        if kind == 'rejected': replay_rejections[data['reason']] += 1

    pipe = Pipeline(profile, record=recorded, fix=fixes.append, compute=False, allow_history=True)
    original_solve = pipe.solver.solve

    def solve(obs, corrected, **kwargs):
        fitted.clear()
        master = pipe.master.id
        item = {'range_differences_m': {aid: (ticks-corrected[master])*TICK_S*C_M_S for aid,ticks in corrected.items()},
                'nlos': {aid:o.nlos for aid,o in obs.items()},
                'clock_sigma_m': kwargs.get('clock_sigmas_m', {})}
        try:
            result = original_solve(obs, corrected, **kwargs)
            item['outcome'] = 'accepted'
            return result
        except ValueError as error:
            item['outcome'] = str(error)
            raise
        finally:
            if fitted:
                best = min(fitted, key=lambda candidate: float(np.dot(candidate.fun,candidate.fun)))
                item['best_candidate_on_bounds'] = bool(np.any(np.abs(best.active_mask)>0))
                item['best_jacobian_condition'] = float(np.linalg.cond(best.jac))
                item['best_normalized_rms'] = float(np.sqrt(np.mean(best.fun**2)))
                try:
                    covariance=np.linalg.inv(best.jac.T@best.jac)*max(1,item['best_normalized_rms']**2)
                    item['best_z95_m'] = float(1.96*math.sqrt(max(0,covariance[2,2])))
                    item['best_h95_m'] = float(2.448*math.sqrt(max(np.linalg.eigvalsh(covariance[:2,:2]))))
                except (ValueError,np.linalg.LinAlgError): pass
            attempts.append(item)

    pipe.solver.solve=solve
    with patch('time.monotonic', lambda:now[0]), patch.object(positioning,'least_squares',fit):
        for row in rows:
            now[0] = datetime.fromisoformat(row['recorded_utc'].replace('Z','+00:00')).timestamp()
            kind,data=row['kind'],row['data']
            if kind=='reset': pipe.reset(data['anchor_id'])
            elif kind=='transport_gap': pipe.transport_gap(data['anchor_id'],data['reason'])
            elif kind=='processing':
                pipe.compute=data['enabled']
                for anchor in profile.anchors: pipe.reset(anchor.id)
            elif kind=='observation':
                observations[data['anchor_id']+':'+data['frame_type']]+=1
                pipe.accept(Observation(**data))
                clocks[pipe.clock_status()]+=1
    report={'source_session':str(args.session),'profile':rows[0]['data']['profile'],
            'read_only':True,'hardware_opened':False,'originals_modified':False,
            'event_counts':dict(events),'logged_rejections':dict(logged_rejections),
            'replay_rejections':dict(replay_rejections),'observations':dict(observations),
            'clock_status_counts':dict(clocks),'solver_attempts':len(attempts),'accepted_fixes':len(fixes),
            'attempt_outcomes':dict(Counter(item['outcome'] for item in attempts)),
            'attempt_details':attempts,'final':pipe.snapshot()}
    destination=ROOT/'verification'/('position-session-diagnostic-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'session-snapshot.jsonl').write_text('\n'.join(json.dumps(row) for row in rows)+'\n',encoding='utf-8')
    (destination/'report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({'report':str(destination/'report.json'),**{k:v for k,v in report.items() if k not in ('profile','attempt_details','observations')}},indent=2))


if __name__=='__main__': main()
