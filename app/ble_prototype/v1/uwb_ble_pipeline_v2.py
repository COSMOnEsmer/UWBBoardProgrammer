"""BLE pipeline revision with correlated TDoA errors and explicit session identity."""
from uwb_ble_pipeline import LivePipeline
from uwb_ble_positioning import CorrelatedSolver


class CorrelatedLivePipeline(LivePipeline):
    def __init__(self, profile, record, fix):
        def labeled_record(kind, data):
            if kind == 'fix':
                data={**data,'engine_id':'UWBBoardProgrammer/StandaloneBLE-pilot'}
            record(kind, data)
        super().__init__(profile, labeled_record, fix)
        self.engine.solver=CorrelatedSolver(profile)
        record('transport',dict(name='BLE',protocol=1,pilot=True,
                                covariance='shared-master',hardware_validated=False))
