"""Survey acquisition and explicit USB Tag preparation; no RTLS operations."""
import asyncio
from itertools import combinations
import json
from pathlib import Path
import re
import subprocess
import time
from .ble_transport import Binding
from .survey_transport import SurveyNetwork
from .survey_tag import UsbSurveyTag
from .survey_geometry import estimate_range,recover_anchors,locate_reference
from . import standalone_flashing as flashing


def survey_bindings(profile):
    anchors=profile.anchors
    if profile.mode!='tdoa_4' or len(anchors)!=4:raise ValueError('Select four-anchor TDoA before Auto Survey')
    if len({a.id for a in anchors})!=4 or len({a.mac.upper() for a in anchors})!=4 or sum(a.role=='master' for a in anchors)!=1:
        raise ValueError('Four unique anchor identities and one master are required')
    bindings=[Binding(a.id,a.mac,a.role) for a in anchors]
    macs=[b.mac.upper() for b in bindings]+[profile.tag_mac.upper()]
    if len(bytes.fromhex(profile.tag_mac))!=8 or len(set(macs))!=5 or len({mac[-4:] for mac in macs})!=5:
        raise ValueError('Anchor and Tag MACs need distinct 16-bit suffixes for survey ranging')
    return bindings


def cancelled(event):
    if event.is_set():raise ValueError('Survey cancelled; active radio leases are restored or expire automatically')


async def capture_graph(profile,log,event,record=lambda *args:None):
    bindings=survey_bindings(profile);edges={};captures=[];errors={}
    async with SurveyNetwork(bindings,log) as network:
        info=dict(network.info)
        for index,(a,b) in enumerate(combinations(bindings,2),1):
            cancelled(event);log(f'Anchor pair {index}/6: {a.anchor_id} / {b.anchor_id}')
            value=await network.measure_pair(a.anchor_id,b.anchor_id,5)
            record('anchor-pair',value)
            if not network.last_restore_acknowledged:raise ValueError('Standalone restoration was not acknowledged; retry after the radio leases expire')
            captures.append(value)
            try:
                estimate=estimate_range(value['records']);edges[tuple(sorted((a.anchor_id,b.anchor_id)))]=estimate
                log(f"Range {estimate['distance_m']:.3f} m / LOS samples {estimate['samples']}")
            except ValueError as error:
                errors[a.anchor_id+' / '+b.anchor_id]=str(error);log(str(error))
    cancelled(event)
    try:geometry=recover_anchors([b.anchor_id for b in bindings],edges)
    except ValueError as error:geometry=None;errors['geometry']=str(error)
    return dict(geometry=geometry,errors=errors,edges=[dict(a=a,b=b,**value) for (a,b),value in edges.items()],captures=captures,board_info=info,simulated=False)


async def capture_reference(profile,geometry,port,usb_serial,log,event,record=lambda *args:None,previous=None,known_position=None,capture_seconds=20):
    if not 5<=capture_seconds<=20:raise ValueError('Reference capture must be 5..20 seconds within the radio lease')
    if previous and previous.get('known_position')!=known_position:
        raise ValueError('Reference coordinates changed; reset reference captures before continuing')
    bindings=survey_bindings(profile);tag=UsbSurveyTag(port,usb_serial,profile.tag_mac)
    await asyncio.to_thread(tag.open)
    previous=previous or {};captures=list(previous.get('captures',[]));ranges=dict(previous.get('ranges',{}));errors=dict(previous.get('errors',{}));quality=dict(previous.get('quality',{}))
    try:
        async with SurveyNetwork(bindings,log,allow_partial=True) as network:
            for index,binding in enumerate(bindings,1):
                if binding.anchor_id in ranges or binding.anchor_id not in network.clients:continue
                cancelled(event);log(f'Tag range {index}/4: {binding.anchor_id}')
                try:
                    result=await network.measure_tag(binding.anchor_id,tag,capture_seconds);record('tag-range',result);captures.append(result)
                    if not network.last_restore_acknowledged:raise ValueError('Anchor restoration pending after Tag ranging')
                except Exception as error:
                    errors[binding.anchor_id]=type(error).__name__+': '+str(error);log(binding.anchor_id+': '+errors[binding.anchor_id])
                    break
                rows=result['records']
                quality[binding.anchor_id]=dict(samples=len(rows),los=sum(r['status']==0 and not r['nlos'] for r in rows),
                                               nlos=sum(r['status']==0 and r['nlos'] for r in rows),failed=sum(r['status']!=0 for r in rows))
                counts=quality[binding.anchor_id];log(f"{binding.anchor_id}: LOS {counts['los']} / NLOS {counts['nlos']} / failed {counts['failed']}")
                try:
                    ranges[binding.anchor_id]=estimate_range(rows);errors.pop(binding.anchor_id,None)
                except ValueError as error:
                    # A quality failure does not invalidate safe measurements
                    # from other stationary anchors. Transport/restore failures
                    # above still stop this capture.
                    errors[binding.anchor_id]=str(error);log(binding.anchor_id+': '+str(error))
        cancelled(event)
        missing=[binding.anchor_id for binding in bindings if binding.anchor_id not in ranges]
        point=locate_reference(geometry['anchors'],ranges) if not missing and geometry is not None else None
        return dict(point=point,complete=not missing,known_position=known_position,
                    ranges=ranges,captures=captures,missing=missing,errors=errors,quality=quality,capture_seconds=capture_seconds,
                    tag_hello=tag.hello,simulated=False)
    finally:tag.close()


def identify_usb_board(root,port,usb_serial):
    import serial
    flashing._identity(port,usb_serial)
    # Read-only ROM query resets an asleep MCU into its short diagnostics window.
    result=subprocess.run([str(Path(root)/'tools/dk6/DK6Programmer.exe'),'-V','0','-P','1000000','-s',port,'-m'],
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30,
                          creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if result.returncode or b'Detected QN9090' not in result.stdout:raise ValueError('USB board did not identify as a QN9090 EVK')
    handle=serial.Serial(port=None,baudrate=3000000,timeout=.1);handle.port=port;handle.rts=False;handle.dtr=False
    with handle:
        end=time.monotonic()+4.5
        while time.monotonic()<end:
            raw=handle.readline();text=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',raw).decode('utf-8',errors='replace')
            start=text.find('{"v":1,')
            if start<0:continue
            try:message=json.JSONDecoder().raw_decode(text[start:])[0]
            except ValueError:continue
            if message.get('kind')=='hello':return message
    raise ValueError('No board identity after reset. Check USB power and the selected port; no firmware was written.')


def prepare_tag(root,profile,port,usb_serial,label,log):
    message=identify_usb_board(root,port,usb_serial)
    if message.get('model')!='Type2DK' or message.get('role')!='tag' or message.get('mac','').upper()!=profile.tag_mac.upper():
        raise ValueError('Selected USB board is not the configured Type2DK Tag; no firmware was written')
    _,entries=flashing.latest_bundle(root)
    entry=next(value for value in entries if value['image_label']==label)
    if label=='tag_setup' and entry.get('auto_survey') is not True:raise ValueError('Auto Survey USB Tag image is missing from the firmware bundle')
    if entry['provisioned_mac']!=profile.tag_mac.upper():raise ValueError('Firmware Tag identity does not match this profile')
    result=flashing.flash_selected(root,entry,port,usb_serial,log)
    if not result.get('program_verify_passed') or not result.get('configuration_acknowledged'):
        raise ValueError('Tag firmware preparation failed; inspect '+result.get('report','the Flash report'))
    return result
