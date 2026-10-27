"""Bridge live BLE observations into the existing validated positioning pipeline.

Call every method on the same worker thread. A reset event is processed before
later observations. This bridge has no radio commands or cloud credentials.
"""
import json
from uwb_ble_receiver import Binding


class LivePipeline:
    def __init__(self, profile, record, fix):
        from uwb_board_programmer.engine import Pipeline
        if profile.mode != 'tdoa_4':
            raise ValueError('Standalone pilot requires the four-anchor TDoA profile')
        profile.validate(require_ports=False, require_aoa=False)
        self.profile = profile
        self.record = record
        self.fix = fix
        self.active = set()
        self.info = {}
        self.engine = Pipeline(profile, record=record, fix=self._fix, raw=lambda raw: None)

    def _fix(self, value):
        self.fix({**value, 'engine_id': 'UWBBoardProgrammer/StandaloneBLE-pilot'})

    def bindings(self):
        return [Binding(a.id, a.mac, a.role) for a in self.profile.anchors]

    def event(self, aid, kind, data):
        from uwb_board_programmer.protocol import parse_line
        self.record('ble_'+kind, dict(anchor_id=aid, **data))
        if kind == 'reset':
            self.engine.reset(aid)
        elif kind == 'connected':
            self.active.add(aid)
            self.info[aid] = data
        elif kind == 'disconnected':
            self.active.discard(aid)
            self.info.pop(aid, None)
        elif kind == 'observation' and aid in self.active:
            self.engine.accept(parse_line(json.dumps(data), aid))
        self.engine.expire()

    def snapshot(self):
        return {**self.engine.snapshot(), 'transport': 'BLE',
                'connected': sorted(self.active), 'info': dict(self.info)}
