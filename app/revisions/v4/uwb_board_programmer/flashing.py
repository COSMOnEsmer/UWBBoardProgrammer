import hashlib,json,os,subprocess,time,threading,queue
from pathlib import Path
from .models import unique_path
from .serial_io import configure_tag,exchange

def bundles(root):
    return sorted((Path(root)/'firmware/releases').glob('*/bundle-manifest.json'),reverse=True)
def images(root,manifest):
    data=json.loads(Path(manifest).read_text(encoding='utf-8'));result={}
    for entry in data['images']:
        path=(Path(root)/entry['file']).resolve()
        if not path.is_relative_to(Path(root).resolve()):raise ValueError('Firmware path outside application')
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Firmware hash mismatch: '+entry['role'])
        result[entry['role']]={**entry,'path':path}
    return result

class Flasher:
    def __init__(self,root,log):self.root=Path(root);self.log=log;self.busy=False
    def flash(self,image,port,revision,model):
        if self.busy:raise ValueError('Flashing already in progress')
        if not port or not port.upper().startswith('COM') or not port[3:].isdigit():raise ValueError('Choose a COM port')
        if int(revision)<image['minimum_evk_revision']:raise ValueError('USB flashing requires EVK Rev.3+; use the vendor SWD procedure for earlier revisions')
        if model!=image['model']:raise ValueError('Selected board model does not match firmware')
        if hashlib.sha256(image['path'].read_bytes()).hexdigest()!=image['sha256']:raise ValueError('Firmware changed after selection')
        exe=self.root/'tools/dk6/DK6Programmer.exe'
        if not exe.is_file():raise FileNotFoundError(exe)
        # SDK application image only, no full-chip erase, no OTP/protection commands.
        command=[str(exe),'-V','0','-P','1000000','-s',port,'-Y','-p',str(image['path']),'-v']
        destination=unique_path(self.root/'data/flash-logs','flash-'+image['role'],'.log')
        self.busy=True
        try:
            self.log('Flashing '+model+' '+image['role']+' on '+port+' — keep USB connected')
            with destination.open('x',encoding='utf-8') as output:
                proc=subprocess.Popen(command,cwd=exe.parent,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
                try:
                    # Programmer progress can use CR and ANSI; preserve exact log, emit short lines.
                    lines=queue.Queue();deadline=time.monotonic()+300
                    def drain():
                        for raw in iter(proc.stdout.readline,b''):lines.put(raw)
                        lines.put(None)
                    threading.Thread(target=drain,daemon=True).start()
                    while True:
                        if time.monotonic()>deadline:raise TimeoutError('Programmer timeout; see flash log')
                        try:raw=lines.get(timeout=.2)
                        except queue.Empty:continue
                        if raw is None:break
                        text=raw.decode(errors='replace');output.write(text);output.flush();self.log(text.strip()[:400])
                    code=proc.wait(timeout=5)
                except Exception:proc.kill();proc.wait();raise
                if code:raise RuntimeError('DK6Programmer returned '+str(code)+'; log '+str(destination))
            self.log('Programmer + verify completed. Checking firmware HELLO on USB...')
            hello=exchange(port,image['baud'],'E2E HELLO',lambda d:d.get('kind')=='hello',timeout=40)
            expected='tag' if image['role'].startswith('tag') else image['role']
            if hello.get('model')!=model or hello.get('role')!=expected or hello.get('version')!=image['version']:raise ValueError('Post-flash HELLO model/role/version mismatch')
            self.last_hello=hello
            self.log('Firmware HELLO verified: '+model+' '+expected+'. RF operation still needs testing.');return destination
        finally:self.busy=False
    def setup_tag(self,available,port,revision,profile):
        for key in ['tag_setup','tag_battery']:
            if key not in available:raise ValueError('Complete Tag firmware bundle required')
        self.flash(available['tag_setup'],port,revision,'Type2DK');time.sleep(2)
        configure_tag(port,profile.baud,profile.tag_mac,profile.blink_interval_ms)
        self.log('Tag MAC/interval acknowledged; programming battery image without full erase')
        self.flash(available['tag_battery'],port,revision,'Type2DK')
        if self.last_hello.get('mac')!=profile.tag_mac.upper() or self.last_hello.get('interval_ms')!=profile.blink_interval_ms:raise ValueError('Battery firmware did not retain the configured Tag MAC/interval; keep USB connected and repeat setup')
        self.log('Tag preparation finished. Reset/power-cycle, then test reception on CR2032; retain the setup image for reconfiguration.')
