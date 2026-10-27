import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app/ble_prototype/v1'))
from uwb_ble_receiver import Binding, Central, FreshGate, advertisement_identity, device_info

def info(**changes):
    value=dict(v=1, model='Type2BP', role='master', mac='0200000000000001',
               boot='AABBCCDD', sequence=10, firmware='pilot', autonomous=True, radio_state='running')
    value.update(changes)
    return json.dumps(value).encode()

def test_info_matches_physical_uwb_identity():
    binding=Binding('A1','0200000000000001','master')
    assert device_info(info(),binding)['boot']=='aabbccdd'
    for changes in [dict(sequence=1.0),dict(mac='0200000000000002'),
                    dict(autonomous=False),dict(radio_state='booting'),dict(role='slave')]:
        with pytest.raises(ValueError):device_info(info(**changes),binding)

def test_freshness_snapshot_and_wrap_and_restart():
    gate=FreshGate(dict(boot='aabbccdd',sequence=0xfffffffe))
    def packet(n,**changes):return dict(boot='aabbccdd',transport_sequence=n,dropped=0,**changes)
    assert gate.accept(packet(0xfffffffd),now=0)==(False,None)
    assert gate.accept(packet(0xffffffff),now=0)==(True,None)
    assert gate.accept(packet(0),now=.5)==(True,None)
    assert gate.accept(packet(2),now=1)==(True,'sequence_gap')
    assert gate.accept(packet(3),now=4)==(True,'rf_stream_gap')
    with pytest.raises(ValueError,match='boot changed'):
        gate.accept(dict(boot='12345678',transport_sequence=4,dropped=0))

def test_only_explicit_unique_bindings_and_contract():
    b=Binding('A1','0200000000000001','master')
    assert advertisement_identity(bytes.fromhex('01010200000000000001'))==(b.mac,b.role)
    with pytest.raises(ValueError):Central([b,b],lambda *args:None)
    with pytest.raises(ValueError):advertisement_identity(b'other device')
