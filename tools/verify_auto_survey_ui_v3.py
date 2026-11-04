"""Render the bilingual calibration UI without acquiring hardware or cloud data."""
from datetime import datetime,timezone
import json
import os
from pathlib import Path
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v10'),str(ROOT/'app/battery_calibration/v1'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
os.environ['QT_QPA_PLATFORM']='offscreen'
from PySide6 import QtWidgets as W
from uwb_board_programmer.gui import Window
from uwb_board_programmer.models import Profile
from uwb_board_programmer.survey_wizard import AutoSurveyDialog

if __name__=='__main__':
    folder=ROOT/'verification'/('auto-survey-ui-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    shutil.copytree(ROOT/'resources',folder/'resources')
    app=W.QApplication([]);window=Window(folder);window.profile=Profile.for_mode('tdoa_4');window.populate_profile()
    window.resize(1600,1000);window.show();window.navigate(2)
    for index,language in enumerate(('en','th')):
        window.language_combo.setCurrentIndex(index);app.processEvents()
        assert window.grab().save(str(folder/(language+'-survey-page.png')))
        dialog=AutoSurveyDialog(folder,window.profile,window.tr,window);dialog.resize(1120,900);dialog.show();app.processEvents()
        for page in range(3):
            dialog.tabs.setCurrentIndex(page);app.processEvents()
            assert dialog.grab().save(str(folder/(language+'-wizard-'+str(page+1)+'.png')))
        dialog.close();app.processEvents()
    window.close()
    print(json.dumps(dict(screenshots=str(folder),automatic_acquisition=False,automatic_cloud=False)))
