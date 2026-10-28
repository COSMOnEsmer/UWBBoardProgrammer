"""Export a new local portable ZIP without recordings, credentials or profiles."""
from pathlib import Path
import hashlib
import json
import zipfile

root=Path(__file__).resolve().parents[1]
folder=root/'releases/desktop-v5/UWB_Board_Programmer_2_1_0'
destination=root/'releases/desktop-v5/UWB_Board_Programmer_2_1_0_Windows_x64.v1.zip'
report_path=destination.with_suffix('.manifest.json')
if destination.exists() or report_path.exists():raise FileExistsError('Preserving earlier portable export.')
manifest=json.loads((folder/'package-manifest.v1.json').read_text(encoding='utf8'))
for entry in manifest['files']:
    if hashlib.sha256((folder/entry['file']).read_bytes()).hexdigest()!=entry['sha256']:
        raise ValueError('Packaged file checksum mismatch: '+entry['file'])
files=[]
with zipfile.ZipFile(destination,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for path in sorted(folder.rglob('*')):
        if not path.is_file():continue
        relative=path.relative_to(folder)
        if relative.parts[0] in ('data','config','verification','vendor','.git'):continue
        archive.write(path,(Path(folder.name)/relative).as_posix());files.append(relative.as_posix())
with zipfile.ZipFile(destination) as archive:
    if archive.testzip() is not None:raise RuntimeError('ZIP integrity failure')
report=dict(file=destination.name,sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
            bytes=destination.stat().st_size,files=len(files),credentials_included=False,
            recordings_included=False,profiles_included=False)
with report_path.open('x',encoding='utf8') as output:json.dump(report,output,indent=2)
print(json.dumps(dict(path=str(destination),**report)))
