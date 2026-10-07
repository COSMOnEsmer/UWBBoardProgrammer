"""Create editable vector branding and high-resolution Windows icons."""
from pathlib import Path
import struct, json
from PySide6 import QtCore, QtGui, QtSvg, QtWidgets

root=Path(__file__).resolve().parents[1]
folder=root/'resources/branding';folder.mkdir(parents=True,exist_ok=True)
svg='''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#163555"/><stop offset="1" stop-color="#091a30"/></linearGradient><linearGradient id="u" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#62e4da"/><stop offset="1" stop-color="#25b4d3"/></linearGradient></defs>
<rect x="4" y="4" width="248" height="248" rx="58" fill="url(#bg)"/>
<rect x="4" y="4" width="248" height="248" rx="58" fill="none" stroke="#44607d" stroke-width="2"/>
<g stroke="#536f92" stroke-width="7" stroke-linecap="round"><path d="M74 49v17m36-17v17m36-17v17M74 190v17m36-17v17m36-17v17M49 88h17m-17 36h17m-17 36h17m124-72h17m-17 36h17m-17 36h17"/></g>
<rect x="64" y="64" width="128" height="128" rx="23" fill="#152f4e" stroke="#547397" stroke-width="3"/>
<path d="M89 100v40c0 18 12 30 29 30s29-12 29-30v-40" fill="none" stroke="url(#u)" stroke-width="14" stroke-linecap="round"/>
<circle cx="158" cy="83" r="8" fill="#ffffff"/>
<g fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round"><path d="M173 65a26 26 0 0 1 14 19m-11-37a47 47 0 0 1 29 34"/></g>
<circle cx="208" cy="207" r="15" fill="#245de8" stroke="#091a30" stroke-width="6"/>
</svg>'''
with (folder/'logo-v1.svg').open('x',encoding='utf8') as f:f.write(svg)
app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
renderer=QtSvg.QSvgRenderer(svg.encode());entries=[];blobs=[]
for size in (16,24,32,48,64,128,256,1024):
    image=QtGui.QImage(size,size,QtGui.QImage.Format_ARGB32);image.fill(QtCore.Qt.transparent)
    painter=QtGui.QPainter(image);renderer.render(painter);painter.end()
    data=QtCore.QByteArray();buffer=QtCore.QBuffer(data);buffer.open(QtCore.QIODevice.WriteOnly);image.save(buffer,'PNG');blob=bytes(data)
    if size==1024:
        with (folder/'logo-v1.png').open('xb') as f:f.write(blob)
    else:blobs.append((size,blob))
offset=6+16*len(blobs)
for size,blob in blobs:
    entries.append(struct.pack('<BBBBHHII',0 if size==256 else size,0 if size==256 else size,0,0,1,32,len(blob),offset));offset+=len(blob)
with (folder/'logo-v1.ico').open('xb') as f:f.write(struct.pack('<HHH',0,1,len(blobs))+b''.join(entries)+b''.join(b for _,b in blobs))
print(json.dumps({'brand':'UWB Board Programmer','icon_sizes':[s for s,_ in blobs],'editable_svg':True}))
