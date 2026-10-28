"""Full 2.1 workspace; BLE dependencies are embedded when packaged."""
from pathlib import Path
import argparse
import json
import os
import sys

sys.coinit_flags=0


def root_path(explicit=None):
    if explicit:return Path(explicit).resolve()
    if os.environ.get('UWB_BOARD_PROGRAMMER_ROOT'):
        return Path(os.environ['UWB_BOARD_PROGRAMMER_ROOT']).resolve()
    origin=Path(sys.executable if getattr(sys,'frozen',False) else __file__).resolve()
    for folder in origin.parents:
        if (folder/'programmer-workspace.json').is_file():return folder
    raise RuntimeError('Application workspace is missing.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path)
    parser.add_argument('--smoke-output',type=Path)
    parser.add_argument('--screenshots',type=Path)
    args=parser.parse_args();root=root_path(args.workspace)
    if not getattr(sys,'frozen',False):
        sys.path[:0]=[str(Path(__file__).parent),str(root/'app/ble_prototype/v1'),
                      str(root/'runtime/ble-bench-v2/Lib/site-packages')]
    from PySide6 import QtCore,QtWidgets as W
    from uwb_board_programmer.gui import Window
    app=W.QApplication(sys.argv);app.setApplicationName('UWB Board Programmer 2.1.0')
    window=Window(root);window.show()
    if args.smoke_output:
        if args.smoke_output.exists():raise FileExistsError(args.smoke_output)
        def finish():
            try:
                if args.screenshots:
                    args.screenshots.mkdir(parents=True,exist_ok=False)
                    for language_index,language in [(0,'en'),(1,'th')]:
                        window.language_combo.setCurrentIndex(language_index)
                        for index in range(window.tabs.count()):
                            window.navigation.setCurrentRow(index);app.processEvents()
                            if not window.grab().save(str(args.screenshots/f'{language}-page-{index+1}.png')):
                                raise RuntimeError('Screenshot failed')
                result=dict(version='2.1.0',pages=window.tabs.count(),
                            anchor_rows=window.anchor_table.rowCount(),device_rows=window.device_table.rowCount(),
                            transport=window.transport_combo.currentData(),firmware_bundles=window.firmware_combo.count(),
                            automatic_acquisition=window.controller is not None,automatic_cloud=window.cloud is not None,
                            packed=bool(getattr(sys,'frozen',False)))
                with args.smoke_output.open('x',encoding='utf8') as output:json.dump(result,output,indent=2)
                window.close();app.exit(0)
            except Exception:
                import traceback
                with args.smoke_output.with_suffix('.error.txt').open('x',encoding='utf8') as output:
                    output.write(traceback.format_exc())
                app.exit(1)
        QtCore.QTimer.singleShot(600,finish)
    return app.exec()


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception:
        import traceback
        from datetime import datetime,timezone
        folder=root_path()/'data/startup-logs';folder.mkdir(parents=True,exist_ok=True)
        with (folder/('integrated-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.txt')).open('x',encoding='utf8') as output:
            output.write(traceback.format_exc())
        raise
