"""Host fault-injection tests against actual candidate C, not hardware acceptance."""
from pathlib import Path
from datetime import datetime,timezone
import json
import re
import struct
import subprocess
import zlib
ROOT=Path(__file__).resolve().parents[1]
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
folder=ROOT/'verification'/('tag-radio-lifecycle-'+stamp);folder.mkdir()
vcvars=Path(r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat')
test=ROOT/'tests/native/tag_radio_recovery'
source=ROOT/'firmware/source/v25-battery-radio-recovery'
batch=folder/'test.cmd';exe=folder/'lifecycle.exe'
with batch.open('x',encoding='utf8') as out:
    out.write('@echo off\ncall "'+str(vcvars)+'" >nul\nif errorlevel 1 exit /b 1\n')
    out.write('cl /nologo /std:c11 /W3 /TC /I"'+str(test)+'" /I"'+str(source)+'" "'+str(test/'test_lifecycle.c')+'" /Fo"'+str(folder/'lifecycle.obj')+'" /Fe"'+str(exe)+'"\nif errorlevel 1 exit /b 1\n"'+str(exe)+'"\n')
proc=subprocess.run(['cmd.exe','/d','/c',str(batch)],cwd=folder,capture_output=True,text=True,errors='replace')
with (folder/'compiler-output.txt').open('x',encoding='utf8') as out:out.write(proc.stdout+proc.stderr)
print(proc.stdout+proc.stderr)
if proc.returncode:raise SystemExit(proc.returncode)
raw=bytes.fromhex(re.search(r'DIAGNOSTIC ([0-9a-f]{40})',proc.stdout).group(1))
assert zlib.crc32(raw[:16])&0xffffffff==int.from_bytes(raw[16:],'little')
assert struct.unpack_from('<II',raw,8)==(1,1) and raw[3]==0x21
report=dict(native_scenarios=10,diagnostic_crc_independently_verified=True,passed=True,hardware_test=False,rf_simulated=False)
with (folder/'report.json').open('x',encoding='utf8') as out:json.dump(report,out,indent=2)
print(json.dumps(dict(report=str(folder/'report.json'),**report)))
