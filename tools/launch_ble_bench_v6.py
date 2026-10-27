"""Launch a separate preview; do not modify the released desktop or runtime."""
import argparse
import json
from pathlib import Path
import sys
sys.coinit_flags=0
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'runtime/ble-bench-v2/Lib/site-packages'),
              str(ROOT/'app/revisions/v4'),str(ROOT/'app/ble_prototype/v1')]
from PySide6 import QtCore,QtWidgets as W
from standalone_bench_gui_v7 import Window

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke-output',type=Path)
    parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args()
    app=W.QApplication(sys.argv);app.setApplicationName('UWB Board Programmer - BLE Pilot')
    window=Window(ROOT);window.show()
    if args.smoke_output:
        if args.smoke_output.exists():raise FileExistsError(args.smoke_output)
        def finish():
            report=dict(rows=window.table.rowCount(),worker_open=window.worker is not None,
                        cloud_open=window.cloud is not None,language_options=window.languages.count())
            if args.screenshots:
                args.screenshots.mkdir(parents=True,exist_ok=False)
                for index,language in [(0,'en'),(1,'th')]:
                    window.languages.setCurrentIndex(index);app.processEvents()
                    if not window.grab().save(str(args.screenshots/(language+'.png'))):raise RuntimeError('Screenshot failed')
            with args.smoke_output.open('x',encoding='utf8') as out:json.dump(report,out,indent=2)
            window.close();app.quit()
        QtCore.QTimer.singleShot(400,finish)
    raise SystemExit(app.exec())
