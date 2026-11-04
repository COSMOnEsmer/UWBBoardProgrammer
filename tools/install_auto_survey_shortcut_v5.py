"""Developer helper: prepare the verified 2.4.0 installation and Desktop shortcut."""
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    report=ROOT/'verification'/('installation-2.4.0-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
    subprocess.run([str(ROOT/'deployment/windows-x64/UWB_Board_Programmer_Launcher_v8.exe'),
                    '--root',str(ROOT),'--prepare-only','--report',str(report)],check=True,timeout=90)
    value=json.loads(report.read_text(encoding='utf8'))
    print(json.dumps(dict(report=str(report),**value)))
