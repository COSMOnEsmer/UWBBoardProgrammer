"""Verify local release integrity, original-source preservation and shortcuts."""
from pathlib import Path
import hashlib,json,struct,zlib
root=Path(__file__).resolve().parents[1]
baseline=json.loads((root/'verification/source-baseline-v1.json').read_text(encoding='utf8'))
assert all(hashlib.sha256(Path(row['source']).read_bytes()).hexdigest()==row['source_sha256'] for row in baseline['files'])
manifest=next((root/'firmware/releases').glob('*/bundle-manifest.json'));data=json.loads(manifest.read_text(encoding='utf8'));images=[]
for row in data['images']:
    path=root/row['file'];binary=path.read_bytes();header=struct.unpack('<11I',binary[:44])
    assert hashlib.sha256(binary).hexdigest()==row['sha256']
    assert sum(header[:8])&0xffffffff==0
    assert zlib.crc32(binary[:40])&0xffffffff==header[10]
    assert row['hardware_validated'] is False
    images.append({'role':row['role'],'bytes':len(binary),'sha256_verified':True,'vector_checksum_verified':True,'header_crc32_verified':True,'hardware_validated':False})
smoke=json.loads((root/'verification/packaged-v2-smoke.json').read_text(encoding='utf8'))
assert smoke['packaged'] and not smoke['automatic_serial_open'] and not smoke['automatic_cloud_connect'] and not smoke['fixture_published']
report={'application':'UWB Board Programmer','version':'2.0.0','active_source':'app/revisions/v3','release':'releases/desktop-v2','original_source_files_preserved':len(baseline['files']),'firmware_images':images,'packaged_smoke':smoke,'hardware_rf_cr2032_and_live_rtls_validation':'pending real-board tests'}
with (root/'verification/release-integrity-v1.json').open('x',encoding='utf8') as f:json.dump(report,f,indent=2)
print(json.dumps({'original_sources_preserved':len(baseline['files']),'firmware_integrity':len(images),'packaged_smoke':'passed','hardware_validated':False}))
