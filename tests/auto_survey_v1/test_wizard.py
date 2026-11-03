import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from itertools import combinations
import hashlib
import json
import numpy as np
import pytest
from PySide6 import QtWidgets as W
from uwb_board_programmer.models import Profile
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.survey_geometry import recover_anchors,locate_reference
from uwb_board_programmer.survey_wizard import AutoSurveyDialog


def test_unknown_coordinates_can_start_identity_validation():
    profile=Profile.for_mode('tdoa_4')
    assert all(anchor.position is None for anchor in profile.anchors)
    assert len(survey_bindings(profile))==4
    profile.tag_mac=profile.anchors[0].mac
    with pytest.raises(ValueError,match='distinct'):survey_bindings(profile)


def test_wizard_requires_measured_axes_and_saves_new_profile(tmp_path,monkeypatch):
    app=W.QApplication.instance() or W.QApplication([])
    monkeypatch.setattr('uwb_board_programmer.survey_wizard.inventory',lambda:[])
    profile=Profile.for_mode('tdoa_4');profile.bounds=[[-2,-2,0],[2,2,3]]
    coords=[[-1,1,1],[1,1,2],[1,-1,1],[-1,-1,1]]
    for anchor,position in zip(profile.anchors,coords):anchor.position=position;anchor.aoa_verified=True;anchor.rx_bias_m=.2
    original=tmp_path/'original-profile.json';original.write_text(json.dumps(profile.to_dict()))
    original_hash=hashlib.sha256(original.read_bytes()).hexdigest()
    actual={anchor.id:np.array(anchor.position) for anchor in profile.anchors}
    edges={tuple(sorted((a,b))):{'distance_m':float(np.linalg.norm(actual[a]-actual[b]))} for a,b in combinations(actual,2)}
    geometry=recover_anchors(list(actual),edges)
    dialog=AutoSurveyDialog(tmp_path,profile)
    try:
        assert not dialog.save_button.isEnabled()
        dialog.measured_x.setText('1');dialog.measured_y.setText('1');dialog.measured_z.setText('1')
        for name,point in [('origin',[0,0,0]),('x',[1,0,0]),('y',[0,1,0]),('z',[0,0,1])]:
            ranges={aid:{'distance_m':float(np.linalg.norm(xyz-point))} for aid,xyz in actual.items()}
            dialog.references[name]={'complete':True,'known_position':point,'ranges':ranges,'report':'unit-fixture-'+name+'.json'}
        with pytest.raises(ValueError,match='Confirm'):dialog.calculate()
        dialog.axes_confirm.setChecked(True);dialog.calculate()
        assert dialog.save_button.isEnabled()
        dialog.restore_battery.setChecked(False)  # Unit fixture must never Flash.
        dialog.save_survey()
        assert dialog.saved_path.exists() and dialog.saved_path!=original
        assert hashlib.sha256(original.read_bytes()).hexdigest()==original_hash
        assert profile.survey_verified is False and profile.anchors[0].rx_bias_m==.2
        saved=json.loads(dialog.saved_path.read_text())
        assert saved['survey_verified'] and not any(a['aoa_verified'] for a in saved['anchors'])
        assert all(a['rx_bias_m']==0 for a in saved['anchors'])
        assert dialog.graph is None  # No anchor-pair graph is required.
        for anchor in saved['anchors']:assert anchor['position']==pytest.approx(actual[anchor['id']],abs=1e-5)
    finally:dialog.close();app.processEvents()
