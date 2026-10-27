"""Keep the validated connector and identify this preview accurately in heartbeats."""
from uwb_board_programmer.cloud import CloudClient as ReleasedCloudClient


class CloudClient(ReleasedCloudClient):
    def ack(self,event,payload):
        if event=='edge:heartbeat':
            payload={**payload,'software_version':'UWBBoardProgrammer/StandaloneBLE-pilot'}
        return super().ack(event,payload)
