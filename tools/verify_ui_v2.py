"""Offline UI review, using an isolated workspace and no hardware operations."""
from pathlib import Path
import json,os,shutil,sys
os.environ['QT_QPA_PLATFORM']='offscreen'
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root/'app/revisions/v3'))
from PySide6 import QtWidgets as W
from uwb_board_programmer.gui import Window
folder=root/'verification/ui-v2';folder.mkdir(parents=True,exist_ok=False)
isolated=folder/'isolated';isolated.mkdir();shutil.copytree(root/'resources',isolated/'resources')
app=W.QApplication([]);window=Window(isolated);window.show();app.processEvents();reports=[]
for language,mode in [('en','hybrid_3'),('th','tdoa_4')]:
    window.language_combo.setCurrentIndex(1 if language=='th' else 0);window.mode_combo.setCurrentIndex(1 if mode=='tdoa_4' else 0)
    for index in range(5):
        window.tabs.setCurrentIndex(index);app.processEvents();path=folder/f'{language}-{mode}-page-{index+1}.png'
        if not window.grab().save(str(path)):raise RuntimeError('Screenshot failed')
        reports.append({'language':language,'mode':mode,'page':index+1,'title':window.page_title.text(),'devices':window.device_table.rowCount(),'anchors':window.anchor_table.rowCount(),'slave_clocks':window.clock_table.rowCount()})
assert window.controller is None and window.cloud is None
with (folder/'report.json').open('x',encoding='utf8') as f:json.dump({'hardware_used':False,'cloud_used':False,'pages':reports},f,ensure_ascii=False,indent=2)
window.close();print(folder)
