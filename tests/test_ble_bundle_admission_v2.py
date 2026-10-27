"""Prevent a diagnostic/partial build from replacing the six-board flash menu."""
import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app/ble_prototype/v1'))
from uwb_ble_flasher_v2 import latest_bundle


def bundle(root, stamp, images):
    path=root/'firmware/releases/_experimental'/stamp/'bundle-manifest.json'
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(dict(created_utc=stamp, images=images)), encoding='utf8')
    return path


def fleet():
    return [dict(image_label=label, config_crc='12345678', version='1.3.3-pilot',
                 model='Type2DK' if label.startswith('tag') else 'Type2BP',
                 anchor_slot='Tag' if label.startswith('tag') else 'A'+str(index+1),
                 role=label if label.startswith('tag') else ('master' if index==0 else 'slave'))
            for index,label in enumerate(('master','slave2','slave3','slave4','tag_setup','tag_battery'))]


def test_newer_tag_only_diagnostic_does_not_hide_complete_fleet(tmp_path):
    images=fleet(); expected=bundle(tmp_path, '001', images)
    partial=copy.deepcopy(images[-2:-1]);partial[0]['version']='1.3.4-diagnostic'
    bundle(tmp_path, '002', partial)
    assert latest_bundle(tmp_path)==(expected, images)


def test_complete_diagnostic_and_malformed_manifests_are_skipped(tmp_path):
    expected=bundle(tmp_path, '001', fleet())
    diagnostics=fleet()
    for entry in diagnostics:entry['version']='1.3.4-diagnostic'
    bundle(tmp_path, '002', diagnostics)
    path=bundle(tmp_path, '003', [])
    path.write_text('{broken', encoding='utf8')
    assert latest_bundle(tmp_path)[0]==expected


def test_wrong_model_slot_and_duplicate_role_are_not_eligible(tmp_path):
    images=fleet(); images[0]['model']='Type2DK'
    bundle(tmp_path, '001', images)
    images=fleet();images[1]['image_label']='master'
    bundle(tmp_path, '002', images)
    with pytest.raises(ValueError, match='six-image'):latest_bundle(tmp_path)
