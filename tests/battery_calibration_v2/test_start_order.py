import asyncio
import struct
import time
import zlib
import pytest
from uwb_board_programmer.ble_transport import Binding
from uwb_board_programmer.survey_transport import SurveyNetwork
from uwb_board_programmer.survey_protocol import TWR

def wire(request,session,index,code=0):
    raw=TWR.pack(1,0x54,request,index,1500,code,0,session&0xffff,0)
    return raw[:-4]+struct.pack('<I',zlib.crc32(raw[:-4])&0xffffffff)

def test_anchor_starts_before_tag_and_pre_ack_timeouts_are_discarded():
    async def exercise():
        net=SurveyNetwork([Binding('A1','0200000000000001','master')],tag_initiator_first=True)
        net.clients={'A1':None};net.info={'A1':{'mac':'0200000000000001'}};net.subscribed={'A1'}
        order=[];identity={};tasks=[]
        async def mode(aid,value,**kwargs):
            order.append(('anchor',value))
            if value==3:
                identity.update(kwargs)
                net.queue.put_nowait((time.monotonic(),'A1',wire(kwargs['request'],kwargs['session'],1,33)))
        async def restore():order.append(('anchors',0));return True
        net.set_mode=mode;net.restore=restore
        class Tag:
            mac='0200000000000101'
            async def set_mode(self,value,**kwargs):
                order.append(('tag',value))
                if value==2:
                    assert order[-2]==('anchor',3)
                    async def fresh():
                        await asyncio.sleep(.01)
                        net.queue.put_nowait((time.monotonic(),'A1',wire(kwargs['request'],kwargs['session'],2)))
                    tasks.append(asyncio.create_task(fresh()))
        value=await net.measure_tag('A1',Tag(),.05)
        await asyncio.gather(*tasks)
        assert value['startup_order']=='anchor-first'
        assert [record['index'] for record in value['records']]==[2]
        assert order[-2:]==[('tag',0),('anchors',0)]
    asyncio.run(exercise())

def test_tag_start_failure_still_restores_the_running_initiator():
    async def exercise():
        net=SurveyNetwork([Binding('A1','0200000000000001','master')],tag_initiator_first=True)
        net.clients={'A1':None};net.info={'A1':{'mac':'0200000000000001'}};net.subscribed={'A1'};order=[]
        async def mode(aid,value,**kwargs):order.append(('anchor',value))
        async def restore():order.append(('anchors',0));return True
        net.set_mode=mode;net.restore=restore
        class Tag:
            mac='0200000000000101'
            async def set_mode(self,value,**kwargs):
                order.append(('tag',value))
                if value==2:raise ConnectionError('Lost Tag start acknowledgement')
        with pytest.raises(ConnectionError,match='acknowledgement'):await net.measure_tag('A1',Tag(),1)
        assert order==[('anchor',1),('anchor',3),('tag',2),('tag',0),('anchors',0)]
    asyncio.run(exercise())
