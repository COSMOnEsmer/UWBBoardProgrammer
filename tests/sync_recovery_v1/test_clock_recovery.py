import math
from types import SimpleNamespace
import numpy as np
import pytest
from uwb_board_programmer.clock_recovery import InterpolatedClockFit,AwaitingSync
from uwb_board_programmer.models import Profile,Observation,TICK_S,C_M_S
from uwb_board_programmer.engine import Pipeline
from uwb_board_programmer.ble_controller import BleController,CaptureState


def trained_clock():
    clock=InterpolatedClockFit();base=(1<<61)+1234
    for i in range(6):clock.add(base+round(i*.5/TICK_S),base+987654+round(i*.5/TICK_S),3)
    return clock,base


def test_integer_clock_mapping_and_no_extrapolation():
    clock,base=trained_clock();assert clock.ready()
    raw=base+round(2.25/TICK_S)
    expected=raw+987654+round(3/(C_M_S*TICK_S))
    assert abs(clock.correct(raw)-expected)<=1
    with pytest.raises(AwaitingSync):clock.correct(base+round(2.75/TICK_S))


def test_stale_fit_and_long_rf_interval_require_new_samples():
    clock,base=trained_clock();clock.last-=3
    assert not clock.ready()
    clock.add(base+round(5/TICK_S),base+987654+round(5/TICK_S),3)
    assert len(clock.samples)==1 and not clock.ready()


def test_validation_rejects_bad_sync_and_excessive_skew():
    for skew in [0,300e-6]:
        clock=InterpolatedClockFit();base=1<<55
        for i in range(6):
            local=round(i*.5/TICK_S)
            noise=round(30e-9/TICK_S) if skew==0 and i%2 else 0
            clock.add(base+local,base+round(local*(1+skew))+noise,0)
        assert not clock.ready()


@pytest.fixture
def profile():
    p=Profile.for_mode('tdoa_4');p.survey_verified=True
    p.bounds=[[0,0,0],[10,8,4]];p.tdoa_sigma_m=.03
    for a,xyz in zip(p.anchors,[[0,0,0],[10,0,0],[0,8,0],[0,0,4]]):a.position=xyz
    return p


def measurement(anchor,frame,rx,tx=None,peer='0200000000000001',boot='12345678'):
    return Observation(anchor.id,peer,frame,1,int(rx),None if tx is None else int(tx),64,
                       None,None,0,0,False,boot,0,tx_bits=64 if tx is not None else 0)


def train_pipeline(p,fixes):
    pipe=Pipeline(p,fix=fixes.append);base=(1<<61)+1234
    def sync(seconds):
        tx=base+round(seconds/TICK_S)
        for i,a in enumerate(p.anchors[1:],1):
            flight=round(np.linalg.norm(np.array(a.position)-p.anchors[0].position)/(C_M_S*TICK_S))
            pipe.accept(measurement(a,'SYNC',tx+flight+i*10_000_000,tx))
    for i in range(6):sync(i*.5)
    assert pipe.clock_status()=='synced'
    return pipe,base,sync


def test_transport_loss_retains_rf_model_and_boot_reset_clears_it(profile):
    pipe,base,sync=train_pipeline(profile,[])
    clock=pipe.clocks[profile.anchors[1].id]
    for reason in ['sequence_gap','firmware_queue_loss','rf_stream_gap']:
        pipe.transport_gap(profile.anchors[1].id,reason)
        assert len(clock.samples)==6 and pipe.clock_status()=='synced'
    pipe.reset(profile.anchors[1].id)
    assert len(pipe.clocks[profile.anchors[1].id].samples)==0
    assert pipe.clock_status()!='synced'


def test_complete_3d_fix_waits_for_future_sync(profile):
    fixes=[];pipe,base,sync=train_pipeline(profile,fixes)
    xyz=np.array([4.,3.,1.]);transmit=base+round(2.75/TICK_S)
    for i,a in enumerate(profile.anchors):
        rx=transmit+round(np.linalg.norm(xyz-a.position)/(C_M_S*TICK_S))+i*10_000_000
        pipe.accept(measurement(a,'BLINK',rx,peer=profile.tag_mac))
    assert not fixes and len(pipe.deferred)==3
    sync(3.)
    assert len(fixes)==1
    assert np.linalg.norm(np.array([fixes[0][axis+'_m'] for axis in 'xyz'])-xyz)<.04


def test_unverified_survey_never_generates_xyz(profile,tmp_path):
    profile.survey_verified=False
    controller=BleController(tmp_path,profile,lambda value:None,lambda value:pytest.fail('No unverified XYZ'),diagnostic=False,autostart_threads=False)
    assert isinstance(controller.pipe,CaptureState)
    with pytest.raises(ValueError):controller.handle_event('__processing__','start',{})
    assert not controller.running
    controller.close()


def test_bench_capture_accumulates_sync_without_coordinates(profile):
    profile.survey_verified=False
    for a in profile.anchors:a.position=None
    state=CaptureState(profile,lambda *a:None);base=1<<55
    for i in range(6):
        tx=base+round(i*.5/TICK_S)
        for k,a in enumerate(profile.anchors[1:],1):
            state.transport_gap(a.id,'firmware_queue_loss')
            state.accept(measurement(a,'SYNC',tx+k*100_000,tx))
    assert state.clock_status()=='synced'
    assert state.snapshot()['fixes']==0
    assert all(c['samples']==6 for c in state.snapshot()['clocks'].values())


def test_legacy_usb_uses_original_regression(profile):
    from uwb_board_programmer.positioning import ClockFit
    profile.transport='usb'
    assert all(isinstance(c,ClockFit) for c in Pipeline(profile).clocks.values())
