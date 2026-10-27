import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from uwb_ble_pipeline import LivePipeline
from uwb_board_programmer.models import Profile


def surveyed():
    p=Profile.for_mode('tdoa_4')
    for a, xyz in zip(p.anchors,[(0,0,1),(8,0,1),(0,8,1),(8,8,4)]):
        a.position=list(xyz)
    return p


def test_bluetooth_does_not_require_usb_and_reset_invalidates_clock_fit():
    events=[]
    pipeline=LivePipeline(surveyed(),lambda *row:events.append(row),lambda value:None)
    aid=pipeline.profile.anchors[1].id
    pipeline.engine.clocks[aid].samples.extend([(1,2),(2,3)])
    pipeline.event(aid,'connected',dict(boot='00000001'))
    pipeline.event(aid,'reset',dict(reason='sequence_gap'))
    assert not pipeline.engine.clocks[aid].samples
    pipeline.event(aid,'disconnected',{})
    assert not pipeline.active and not pipeline.info
    assert events[1][0]=='ble_reset'


def test_unset_survey_and_wrong_mode_rejected_before_bluetooth():
    with pytest.raises(ValueError):LivePipeline(Profile.for_mode('tdoa_4'),lambda *a:None,lambda *a:None)
    p=surveyed();p.mode='hybrid_3'
    with pytest.raises(ValueError):LivePipeline(p,lambda *a:None,lambda *a:None)
