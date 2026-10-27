import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from uwb_ble_wire import encode,decode,fragments,Reassembler

def frame(sequence=7,**changes):
    values=dict(boot=0xaabbccdd,sequence=sequence,role=0,rx_bits=64,tx_bits=64,
        frame_type=1,frame_number=0,peer_mac='0200000000000001',
        rx=(1<<63)+123,tx=(1<<62)+77,az_q7=-128,el_q7=256,az_fom=90,el_fom=85)
    values.update(changes);return encode(**values)

def test_full_rf_epochs_are_exact():
    record=decode(frame());assert int(record['rx_timestamp_hex'],16)==(1<<63)+123
    assert int(record['tx_timestamp_hex'],16)==(1<<62)+77
    assert record['azimuth_deg']==-1 and record['elevation_deg']==2

@pytest.mark.parametrize('payload',[20,61,182,244])
def test_mtu_fragmentation_out_of_order_and_duplicates(payload):
    pieces=fragments(frame(),payload);reader=Reassembler();result=None
    for piece in reversed(pieces):result=reader.accept(piece) or result
    assert result['transport_sequence']==7 and not reader.pending
    assert all(reader.accept(piece) is None for piece in pieces)

def test_partial_timeout_and_connection_reset():
    pieces=fragments(frame());reader=Reassembler(ttl_s=.5)
    reader.accept(pieces[0],now=0);reader.accept(pieces[1],now=1)
    assert reader.pending[7]['chunks'].keys()=={1}
    reader.reset();assert not reader.pending and not reader.seen

def test_crc_rejects_corruption():
    raw=bytearray(frame());raw[38]^=1
    with pytest.raises(ValueError,match='CRC'):decode(raw)

def test_conflicting_duplicate_and_pending_limit():
    pieces=fragments(frame());reader=Reassembler(max_pending=2);reader.accept(pieces[0])
    altered=pieces[0][:-1]+bytes([pieces[0][-1]^1])
    with pytest.raises(ValueError,match='duplicate'):reader.accept(altered)
    for seq in range(5):reader.accept(fragments(frame(seq))[0])
    assert len(reader.pending)==2

def test_40_bit_blink_and_invalid_width():
    r=decode(frame(rx_bits=40,rx=(1<<40)-1,tx_bits=0,tx=0,frame_type=0))
    assert r['frame_type']=='BLINK' and r['tx_timestamp_hex'] is None
    with pytest.raises(ValueError,match='overflow'):frame(rx_bits=40)

def test_interleaved_frame_numbers_may_repeat():
    a=fragments(frame(11));b=fragments(frame(12));reader=Reassembler();results=[]
    for x,y in zip(a,b):
        for part in (x,y):
            result=reader.accept(part)
            if result:results.append(result)
    assert [r['transport_sequence'] for r in results]==[11,12]
    assert all(r['frame_number']=='0' for r in results)
