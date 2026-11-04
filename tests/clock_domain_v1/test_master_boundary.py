import pytest
from uwb_board_programmer.clock_recovery import InterpolatedClockFit,AwaitingSync
from uwb_board_programmer.models import TICK_S,C_M_S

HZ=499_200_000*128

def clock(ppm=1.,points=(0,.5,1,1.5,3,3.5,4)):
    c=InterpolatedClockFit()
    for seconds in points:
        tx=round(seconds*HZ);rx=round(tx*(1+ppm*1e-6))+123456
        c.add(rx,tx,1.23)
    return c

@pytest.mark.parametrize('ppm',[.1,1.,150.,-.1,-1.,-150.])
def test_same_master_gap_is_allowed_for_fast_and_slow_slaves(ppm):
    c=clock(ppm);assert len(c.samples)==7 and c.ready()
    rx=round(2*HZ*(1+ppm*1e-6))+123456
    assert abs(c.correct(rx)-(2*HZ+round(1.23/(C_M_S*TICK_S))))<=2

def test_three_second_validation_span_uses_master_domain_too():
    c=clock(100,points=(0,1.5,3,3.5,4,4.5))
    assert c.validation_count==4 and c.ready()

def test_real_master_gap_still_discards_old_validation():
    c=clock();tx=round(6*HZ);rx=round(tx*(1+1e-6))+123456
    c.add(rx,tx,1.23);assert len(c.samples)==1 and not c.ready()
    with pytest.raises(AwaitingSync):c.correct(rx)

def test_master_limit_is_not_relaxed_even_one_tick():
    c=clock();tx=round(5.5*HZ)+1;rx=round(tx*(1+1e-6))+123456
    c.add(rx,tx,1.23);assert len(c.samples)==1

def test_no_extrapolation_or_stale_clock_acceptance(monkeypatch):
    c=clock()
    with pytest.raises(AwaitingSync):c.correct(c.samples[-1][0]+1000)
    monkeypatch.setattr('uwb_board_programmer.clock_recovery.time.monotonic',lambda:c.last+3)
    assert not c.ready()

def test_bad_noise_and_excessive_skew_remain_rejected():
    assert not clock(500).ready()
    c=InterpolatedClockFit()
    for n in range(10):
        tx=n*HZ//2;rx=tx+(5000 if n%2 else -5000);c.add(rx,tx,0)
    assert c.rms_s>2e-9 and not c.ready()
