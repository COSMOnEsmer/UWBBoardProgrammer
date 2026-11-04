"""Capture registration UI with explicit static example geometry, no live traffic."""
from datetime import datetime,timezone
from pathlib import Path
import json,os,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v16'),str(ROOT/'app/battery_calibration/v2'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from PySide6 import QtCore,QtWidgets as W
from uwb_board_programmer.gui import Window
from uwb_board_programmer.models import Profile
from uwb_board_programmer.coordinates import align_profile
from uwb_board_programmer.alignment_dialog import AlignmentDialog

def main():
    app=W.QApplication([]);w=Window(ROOT);w.language_combo.setCurrentIndex(0)
    p=Profile.for_mode('tdoa_4');p.coordinate_frame='survey';p.survey_verified=True;p.site_id='example-site';p.floor_id='example-floor';p.bounds=[[-2,-2,0],[2,2,2]]
    for a,xyz in zip(p.anchors,[[-.444,.452,.891],[.881,.469,1.891],[1.318,-.389,.779],[-1.132,-.426,.518]]):a.position=xyz
    geometry=dict(origin_x=0,origin_y=0,length=4,width=4,height=2,elevation=0,level_index=0,meters_per_pixel=.01)
    w.profile=align_profile(p,0,[1.132,.426,0],geometry,True);w.populate_profile();w.resize(1568,1003);w.show()
    w.statusBar().showMessage('UI verification: static geometry example / no live RF or cloud connection')
    target=ROOT/'verification'/('floor-ui-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));target.mkdir()
    def settle():
        for _ in range(6):app.processEvents();QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
    w.navigation.setCurrentRow(2);settle();assert w.grab().save(str(target/'floor-survey.png'))
    dialog=AlignmentDialog(w.profile,w);dialog.resize(1120,820);dialog.show();settle();assert dialog.grab().save(str(target/'alignment-preview.png'))
    dialog.reject();w.language_combo.setCurrentIndex(1);settle()
    dialog=AlignmentDialog(w.profile,w);dialog.resize(1120,820);dialog.show();settle();assert dialog.grab().save(str(target/'alignment-preview-th.png'));dialog.reject()
    assert w.controller is None and w.cloud is None;w.close()
    print(json.dumps(dict(directory=str(target),captures=3,static_geometry=True,live_rf=False,cloud=False)))

if __name__=='__main__':main()
