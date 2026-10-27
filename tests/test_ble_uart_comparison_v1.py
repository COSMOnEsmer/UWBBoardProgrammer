import copy
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from compare_ble_uart_pilot_v1 import compare


def sample():
    return dict(kind='rx',boot='1234abcd',peer_mac='0200000000000101',
                frame_type='BLINK',frame_number='4294967295',status=0,
                message_control=16,timestamp_bits=64,tx_timestamp_bits=0,
                rx_timestamp_hex='f123456789abcdef',tx_timestamp_hex=None,
                az_fom=100,el_fom=100,nlos=0,azimuth_deg=-11.171875,
                elevation_deg=33.0703125)


def test_real_wire_precision_and_uart_display_rounding_are_compared_separately():
    ble=sample();uart=copy.deepcopy(ble);uart['elevation_deg']=33.070313
    report=compare([ble],[uart])
    assert report['passed'] and report['matched_records']==1


def test_one_tick_mismatch_cannot_pass_as_a_matching_measurement():
    ble=sample();uart=copy.deepcopy(ble);uart['rx_timestamp_hex']='f123456789abcdee'
    report=compare([ble],[uart])
    assert not report['passed'] and report['matched_records']==0


def test_matching_timestamp_does_not_hide_corrupted_quality_or_frame_data():
    ble=sample();uart=copy.deepcopy(ble);uart['frame_number']='1';uart['status']=1
    report=compare([ble],[uart])
    assert not report['passed'] and report['matched_records']==1
    assert set(report['mismatches'][0]['fields'])=={'frame_number','status'}
