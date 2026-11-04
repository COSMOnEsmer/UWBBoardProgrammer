import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets as W
from uwb_board_programmer.spatial_view import FloorPlot
from uwb_board_programmer.panels import Panel

def app():return W.QApplication.instance() or W.QApplication([])

def test_missing_samples_hold_last_point_and_do_not_refresh_age(monkeypatch):
    application=app();clock=[10.];monkeypatch.setattr('uwb_board_programmer.spatial_view.time.monotonic',lambda:clock[0])
    view=FloorPlot();sample=dict(x_m=1,y_m=2,z_m=3,born=10.,accepted=False)
    view.set_live(sample,[]);clock[0]=14;view.set_live(sample,[]);view.set_live(None,[])
    assert view.last==10 and view.live['x_m']==1 and len(view.trail)==1
    clock[0]=41;view.prune_path();assert view.trail==[] and view.live is not None
    view.clear_position();assert view.live is None;view.close()

def test_path_retains_only_last_thirty_seconds(monkeypatch):
    application=app();clock=[0.];monkeypatch.setattr('uwb_board_programmer.spatial_view.time.monotonic',lambda:clock[0])
    view=FloorPlot()
    for t in range(38):
        clock[0]=float(t);view.set_live(dict(x_m=t,y_m=0,z_m=1,born=float(t),accepted=True),[])
    assert [row['born'] for row in view.trail]==[float(t) for t in range(7,38)]
    view.close()

def test_detach_preserves_widgets_and_close_reattaches():
    application=app();owner=W.QMainWindow();panel=Panel('Test',owner);owner.setCentralWidget(panel)
    button=W.QPushButton('Live control');panel.body_layout.addWidget(button);events=[];button.clicked.connect(lambda:events.append(1))
    owner.show();panel.toggle();assert panel.body.isHidden();panel.toggle()
    panel.float_or_dock();application.processEvents();assert panel.dialog is not None and panel.body.parentWidget()==panel.dialog
    button.click();panel.dialog.close();application.processEvents()
    assert panel.dialog is None and panel.body.parentWidget()==panel and events==[1]
    owner.close()
