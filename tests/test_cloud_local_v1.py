import json,threading,time
from socketserver import ThreadingMixIn
from wsgiref.simple_server import make_server,WSGIServer,WSGIRequestHandler
import socketio
from uwb_board_programmer.cloud import CloudClient
from uwb_board_programmer.models import Profile
class Threaded( ThreadingMixIn,WSGIServer):daemon_threads=True
class Quiet(WSGIRequestHandler):
    def log_message(self,*args):pass
def test_socketio_auth_ack_and_rejected_event_local_only():
    p=Profile()
    for a,pos in zip(p.anchors,[[0,0,2],[8,0,2],[0,6,3]]):a.position=pos
    config={'site':{'id':p.site_id},'floors':[{'id':p.floor_id}],'anchors':[{'id':a.id,'floorId':p.floor_id,'role':a.role,'posXM':a.position[0],'posYM':a.position[1],'posZM':a.position[2]} for a in p.anchors]}
    server=socketio.Server(async_mode='threading');received=[]
    @server.on('connect',namespace='/edge')
    def connect(sid,environ,auth):return auth=={'token':'local-unit-test'}
    @server.on('edge:heartbeat',namespace='/edge')
    def heartbeat(sid,payload):received.append(('heartbeat',payload));return {'ok':True}
    @server.on('edge:position',namespace='/edge')
    def position(sid,payload):received.append(('position',payload));return {'ok':False,'error':'unit-test rejection'} if payload['z_m']<0 else {'ok':True}
    socket_app=socketio.WSGIApp(server)
    def application(environ,start):
        if environ['PATH_INFO']=='/api/v1/edge/config':
            assert environ['HTTP_AUTHORIZATION']=='Bearer local-unit-test';body=json.dumps({'ok':True,'data':config}).encode();start('200 OK',[('Content-Type','application/json'),('Content-Length',str(len(body)))]);return [body]
        return socket_app(environ,start)
    http=make_server('127.0.0.1',0,application,server_class=Threaded,handler_class=Quiet);worker=threading.Thread(target=http.serve_forever,daemon=True);worker.start();logs=[]
    client=CloudClient(p,'local-unit-test','local-test-gateway',logs.append,lambda:{'clock_status':'unknown','devices':[]},base='http://127.0.0.1:'+str(http.server_port));client.start()
    try:
        deadline=time.monotonic()+12
        while not client.connected and time.monotonic()<deadline:time.sleep(.05)
        assert client.connected,logs
        fix={'site_id':p.site_id,'floor_id':p.floor_id,'tag_id':p.tag_id,'x_m':2,'y_m':3,'z_m':1.25,'accuracy_m':.2,'num_anchors_used':3,'residual':.03,'time':'2026-10-07T01:00:00Z'}
        client.publish_fix(fix);client.publish_fix({**fix,'z_m':-1})
        while len([x for x in received if x[0]=='position'])<2 and time.monotonic()<deadline:time.sleep(.05)
        assert received[0][0]=='heartbeat';assert len([x for x in received if x[0]=='position'])==2
        assert client.ack_error==1;assert client.ack_ok>=2;assert any('rejected' in x for x in logs)
    finally:client.close();http.shutdown();http.server_close()
