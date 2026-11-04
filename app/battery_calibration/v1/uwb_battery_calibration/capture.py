"""Tag BLE + at most master/target GATT links; no COM access during capture."""
from uwb_board_programmer.ble_controller import discover
from uwb_board_programmer.survey_workflow import survey_bindings,cancelled
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_geometry import estimate_range
from .ble_tag import BleSurveyTag

async def inspect_tag(profile,log):
    async with BleSurveyTag(profile.tag_mac,log) as tag:return dict(tag.info)

async def capture_reference_ble(profile,log,event,record=lambda *args:None,previous=None,known_position=None,capture_seconds=20):
    if not 5<=capture_seconds<=20:raise ValueError('Reference capture must be 5..20 seconds')
    if previous and previous.get('known_position')!=known_position:raise ValueError('Reference position changed; restart the survey')
    bindings=survey_bindings(profile);previous=previous or {}
    ranges=dict(previous.get('ranges',{}));captures=list(previous.get('captures',[]))
    quality=dict(previous.get('quality',{}));errors=dict(previous.get('errors',{}));boards=dict(previous.get('board_info',{}))
    tag_info={};remaining=None;session_error=None;aborted=False
    try:
        async with BleSurveyTag(profile.tag_mac,log) as tag:
            tag_info=dict(tag.info)
            available={v['mac'] for v in await discover(5,'active')}
            for target in bindings:
                if target.anchor_id in ranges or target.mac.upper() not in available:continue
                cancelled(event)
                selected=[b for b in bindings if b.anchor_id==target.anchor_id or b.role=='master' and b.mac.upper() in available]
                log('BLE Tag range: '+target.anchor_id)
                try:
                    async with SurveyNetwork(selected,log,allow_partial=True) as network:
                        if target.anchor_id not in network.clients:continue
                        result=await network.measure_tag(target.anchor_id,tag,capture_seconds)
                        record('tag-ble-range',result);captures.append(result);boards.update(network.info)
                        if not network.last_restore_acknowledged:raise ValueError('Anchor restoration was not acknowledged')
                except Exception as error:
                    errors[target.anchor_id]=type(error).__name__+': '+str(error);log(errors[target.anchor_id]);aborted=True;break
                rows=result['records'];q=dict(samples=len(rows),los=sum(r['status']==0 and not r['nlos'] for r in rows),
                                              nlos=sum(r['status']==0 and r['nlos'] for r in rows),failed=sum(r['status']!=0 for r in rows))
                quality[target.anchor_id]=q;log(f"{target.anchor_id}: LOS {q['los']} / NLOS {q['nlos']} / failed {q['failed']}")
                try:ranges[target.anchor_id]=estimate_range(rows);errors.pop(target.anchor_id,None)
                except ValueError as error:errors[target.anchor_id]=str(error);log(str(error))
            remaining=max(0,int(tag.remaining()))
    except Exception as error:session_error=type(error).__name__+': '+str(error);log(session_error)
    cancelled(event)
    missing=[b.anchor_id for b in bindings if b.anchor_id not in ranges]
    if session_error:errors['Tag BLE']=session_error
    else:errors.pop('Tag BLE',None)
    return dict(complete=not missing and not session_error and not aborted,known_position=known_position,ranges=ranges,captures=captures,
                quality=quality,errors=errors,missing=missing,tag_info=tag_info,tag_window_remaining_s=remaining,
                board_info=boards,tag_control='ble',capture_seconds=capture_seconds,simulated=False,
                radio_restoration_acknowledged=not session_error and not aborted)
