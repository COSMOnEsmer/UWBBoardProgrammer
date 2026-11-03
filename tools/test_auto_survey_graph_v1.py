"""Real four-anchor link diagnostics; writes new reports and never publishes RTLS."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import threading
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/revisions/v8'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.ble_controller import run_ble
from uwb_board_programmer.models import Profile,save_new
from uwb_board_programmer.survey_workflow import capture_graph

if __name__=='__main__':
    directory=ROOT/'verification'/('auto-survey-links-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    directory.mkdir(exist_ok=False)
    try:
        result=run_ble(capture_graph(Profile.for_mode('tdoa_4'),lambda line:print(line,flush=True),threading.Event(),
                                    lambda name,data:save_new(directory,name,data)))
    except Exception as error:result=dict(error=type(error).__name__+': '+str(error),simulated=False)
    report=directory/'report.json';report.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(report=str(report),accepted_edges=len(result.get('edges',[])),errors=result.get('errors'),error=result.get('error'))),flush=True)
