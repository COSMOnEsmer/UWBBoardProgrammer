"""Render native Qt workflows at laptop and desktop sizes; no acquisition/Flash."""
from datetime import datetime,timezone
from pathlib import Path
import json,os,sys
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v15'),str(ROOT/'app/battery_calibration/v2'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from PySide6 import QtCore,QtWidgets as W
from uwb_board_programmer.gui import Window

def main():
    app=W.QApplication([]);window=Window(ROOT);window.show()
    target=ROOT/'verification'/('design-v15-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));target.mkdir()
    checks=[]
    for width,height in [(1366,768),(1568,1003),(1920,1080)]:
        window.resize(width,height)
        for language_index,language in [(0,'en'),(1,'th')]:
            window.language_combo.setCurrentIndex(language_index)
            for page in range(6):
                window.navigation.setCurrentRow(page)
                for _ in range(6):
                    app.processEvents();QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
                scroll=window.tabs.widget(page);scroll.verticalScrollBar().setValue(0)
                name=f'{width}x{height}-{language}-{page+1}.png'
                assert window.grab().save(str(target/name))
                assert window.controller is None and window.cloud is None
                checks.append(dict(width=width,height=height,language=language,page=page+1,screenshot=name))
    window.close()
    with (target/'report.json').open('x',encoding='utf8') as output:json.dump(dict(native_qt=True,automatic_acquisition=False,automatic_cloud=False,captures=checks),output,indent=2)
    print(json.dumps(dict(report=str(target/'report.json'),screenshots=len(checks))))

if __name__=='__main__':main()
