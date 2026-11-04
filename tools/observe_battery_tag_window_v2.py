"""Observe finite Tag advertising and continued UWB BLINK, not battery current."""
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app/battery_calibration/v2'),str(ROOT/'app/revisions/v11'),str(ROOT/'app/ble_prototype/v1'),str(ROOT/'runtime/ble-bench-v2/Lib/site-packages')]
from uwb_board_programmer.models import Profile
from uwb_board_programmer.survey_workflow import survey_bindings
from uwb_board_programmer.ble_transport import Central
from uwb_board_programmer.ble_controller import run_ble
from uwb_battery_calibration.ble_tag import BleSurveyTag,advertisement_tag
from uwb_ble_wire import SERVICE_UUID

async def observe(folder):
    from bleak import BleakScanner
    profile=Profile.for_mode('tdoa_4');ids={a.id for a in profile.anchors}
    async with BleSurveyTag(profile.tag_mac,lambda line:print(line,flush=True)) as tag:
        info=tag.info;expected_end=tag.connected_at+info['ble_window_remaining_s']
    began=time.monotonic();deadline=expected_end+40;last_adv=[began];adv_count=[0];last_blink={};counts={};groups={};matched=[0,0.];errors=[]
    def detected(device,adv):
        if advertisement_tag(adv.service_data.get(SERVICE_UUID,b''),profile.tag_mac):last_adv[0]=time.monotonic();adv_count[0]+=1
    with (folder/'events.jsonl').open('x',encoding='utf8') as output:
        def emit(aid,kind,data):
            if kind=='raw_ble':return
            output.write(json.dumps(dict(utc=datetime.now(timezone.utc).isoformat(),anchor=aid,kind=kind,data=data))+'\n');output.flush()
            if kind=='error':errors.append(dict(anchor=aid,**data))
            if kind!='observation' or data.get('status') or data.get('frame_type')!='BLINK' or data.get('peer_mac')!=profile.tag_mac:return
            now=time.monotonic();last_blink[aid]=now;counts[aid]=counts.get(aid,0)+1
            key=data['frame_number'];group=groups.setdefault(key,{})
            if group and now-min(group.values())>2.5:group.clear()
            group[aid]=now
            if set(group)==ids:matched[0]+=1;matched[1]=now;group.clear()
        central=Central(survey_bindings(profile),emit,scan_mode='active');task=asyncio.create_task(central.run())
        try:
            async with BleakScanner(detected,scanning_mode='passive'):
                print(json.dumps(dict(observation_started=True,remaining_window_s=max(0,int(expected_end-began)),deadline_s=int(deadline-began))),flush=True)
                last_log=0
                while time.monotonic()<deadline:
                    now=time.monotonic()
                    if now-last_log>=30:
                        print(json.dumps(dict(tag_adverts=adv_count[0],blink_counts=counts,matched_frames=matched[0],window_remaining_s=max(0,int(expected_end-now)))),flush=True);last_log=now
                    if adv_count[0] and now>expected_end+8 and now-last_adv[0]>8 and matched[1]>last_adv[0]+5:break
                    await asyncio.sleep(1)
        finally:central.stop.set();await task
    return dict(tag_info=info,tag_adverts_observed=adv_count[0],blink_counts=counts,matched_frames=matched[0],
                ble_window_closed_and_common_blink_continued=bool(adv_count[0] and time.monotonic()-last_adv[0]>8 and matched[1]>last_adv[0]+5),
                errors=errors,usb_opened=False,simulated=False,current_consumption_measured=False,battery_lifetime_validated=False,
                limitation='Advertising cessation and continued RF are observable; actual MCU sleep/current requires independent measurement.')

if __name__=='__main__':
    folder=ROOT/'verification'/('battery-window-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir()
    try:value=run_ble(observe(folder))
    except Exception as error:value=dict(error=type(error).__name__+': '+str(error),simulated=False)
    with (folder/'report.json').open('x',encoding='utf8') as output:json.dump(value,output,indent=2)
    print(json.dumps(dict(report=str(folder/'report.json'),**value)),flush=True)
