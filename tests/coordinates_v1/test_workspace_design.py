import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import pytest
from PySide6 import QtCore,QtWidgets as W
from uwb_board_programmer.gui import Window

APP=W.QApplication.instance() or W.QApplication([])
ROOT=Path(__file__).resolve().parents[2]

def settle():
    for _ in range(5):APP.processEvents()

@pytest.fixture
def window():
    w=Window(ROOT);w.show();settle()
    yield w
    w.close();settle()

def test_no_mdi_or_nested_native_title_bars(window):
    assert not window.findChildren(W.QMdiArea)
    assert len(window.workspace_panels)==6
    assert window.activity_dock.widget().collapsed
    assert all(d.titleBarWidget().objectName()=='PanelHeader' for group in window.workspace_panels for name,d in group.items() if name!='Tag coordinates')

def test_floating_attach_keeps_same_live_controls(window):
    window.navigation.setCurrentRow(2);settle()
    dock=window.workspace_panels[2]['Anchor geometry'];panel=dock.widget();table=window.anchor_table
    table.item(0,3).setText('1.234');panel.float_or_dock();settle()
    assert dock.isFloating() and panel.detach.text()=='Attach'
    assert window.anchor_table is table and table.item(0,3).text()=='1.234'
    panel.detach.click();settle()
    assert not dock.isFloating() and table.item(0,3).text()=='1.234'
    panel.float_or_dock();settle();dock.close();settle();assert not dock.isFloating()

def test_advanced_expand_updates_page_height_and_restores_fields(window):
    window.navigation.setCurrentRow(2);settle();workspace=window.panel_workspaces[2]
    panel=window.workspace_panels[2]['Measurement quality'].widget();height=workspace.minimumHeight()
    assert panel.collapsed
    panel.toggle();settle();assert not panel.collapsed and workspace.minimumHeight()>height
    assert window.sigma_t.isVisibleTo(panel)
    panel.toggle();settle();assert panel.collapsed

def test_map_area_divider_is_resizable(window):
    window.navigation.setCurrentRow(3);settle();workspace=window.panel_workspaces[3];d=window.workspace_panels[3]
    before=d['Floor view'].width()
    workspace.resizeDocks([d['Floor view'],d['Clock synchronization']],[600,550],QtCore.Qt.Horizontal);settle()
    assert abs(d['Floor view'].width()-before)>30
    assert d['Floor view'].width()>300 and d['Clock synchronization'].width()>300

@pytest.mark.parametrize('size',[(1366,768),(1920,1080)])
def test_main_controls_are_inside_their_panels_at_laptop_and_desktop_sizes(window,size):
    window.resize(*size);settle()
    for index,controls in [(0,[window.device_table,window.flash_button,window.tag_image]),(2,[window.anchor_table,window.site,window.auto_survey_button]),(3,[window.open_button,window.plot]),(4,[window.gateway_id,window.cloud_connect,window.gateway_import_button])]:
        window.navigation.setCurrentRow(index);settle()
        for control in controls:
            parent=control.parentWidget()
            assert control.isVisibleTo(parent)
            assert control.y()+control.height()<=parent.height()+2,(size,index,control.objectName(),control.geometry(),parent.size())
    assert not window.controller and not window.cloud
