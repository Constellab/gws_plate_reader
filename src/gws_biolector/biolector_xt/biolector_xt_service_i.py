
from abc import abstractmethod
from typing import List

from gws_biolector.biolector_xt.grpc.biolectorxtremotecontrol_pb2 import (
    ContinueProtocolResponse, ExperimentInfo, ProtocolInfo,
    StartProtocolResponse, StatusUpdateStreamResponse, StdResponse,
    StopProtocolResponse)


class BiolectorXTServiceI():
    """Interface for Biolector XT Service
    """

    @abstractmethod
    def get_protocols(self) -> List[ProtocolInfo]:
        pass

    @abstractmethod
    def get_experiments(self) -> List[ExperimentInfo]:
        pass

    @abstractmethod
    def upload_protocol(self, file_path: str) -> StdResponse:
        pass

    @abstractmethod
    def start_protocol(self, protocol_id: str) -> StartProtocolResponse:
        pass

    @abstractmethod
    def stop_current_protocol(self) -> StopProtocolResponse:
        pass

    @abstractmethod
    def pause_current_protocol(self) -> None:
        pass

    @abstractmethod
    def resume_current_protocol(self) -> ContinueProtocolResponse:
        pass

    @abstractmethod
    def download_experiment(self, experiment_id: str) -> str:
        pass

    @abstractmethod
    def get_status_update_stream(self) -> StatusUpdateStreamResponse:
        pass
