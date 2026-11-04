"""Windows DPAPI, user scoped; no plaintext password/token file."""
import ctypes,base64,json,os
from ctypes import wintypes
from pathlib import Path
from .models import save_new
class Blob(ctypes.Structure):_fields_=[('length',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]
def crypt(data,decrypt=False):
    if os.name!='nt':raise RuntimeError('Credential storage requires Windows DPAPI')
    array=(ctypes.c_ubyte*len(data)).from_buffer_copy(data);src=Blob(len(data),array);dst=Blob()
    api=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    ctypes.windll.kernel32.LocalFree.argtypes=[ctypes.c_void_p]
    ctypes.windll.kernel32.LocalFree.restype=ctypes.c_void_p
    if not api(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)):raise ctypes.WinError()
    try:return ctypes.string_at(dst.data,dst.length)
    finally:ctypes.windll.kernel32.LocalFree(dst.data)
def save(root,token,gateway_id):
    payload=json.dumps({'token':token,'gateway_id':gateway_id}).encode()
    return save_new(Path(root)/'data/credentials','gateway',{'dpapi_user_scope':base64.b64encode(crypt(payload)).decode()})
def load(path):
    data=json.loads(Path(path).read_text(encoding='utf-8'))
    return json.loads(crypt(base64.b64decode(data['dpapi_user_scope']),True))
