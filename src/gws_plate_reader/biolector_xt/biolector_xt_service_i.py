
from abc import abstractmethod
from datetime import datetime
from typing import List

from gws_core import MessageDispatcher
from gws_plate_reader.biolector_xt.biolector_xt_types import (
    BiolectorXTExperiment, BiolectorXTProtocol)
from gws_plate_reader.biolector_xt.grpc.biolectorxtremotecontrol_pb2 import (
    ContinueProtocolResponse, ExperimentInfo, ProtocolInfo,
    StartProtocolResponse, StatusUpdateStreamResponse, StdResponse,
    StopProtocolResponse)


class BiolectorXTServiceI():
    """Interface for Biolector XT Service
    """

    message_dispatcher: MessageDispatcher = None

    def __init__(self, message_dispatcher: MessageDispatcher = None) -> None:
        if message_dispatcher:
            self.message_dispatcher = message_dispatcher
        else:
            self.message_dispatcher = MessageDispatcher()

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

    def get_biolector_experiments(self) -> List[BiolectorXTExperiment]:
        """Method to get the biolector experiments with protocol information

        """

        experiments = self.get_experiments()

        protocols = self.get_protocols()

        biolector_experiments: List[BiolectorXTExperiment] = []

        for experiment in experiments:
            experiment.protocol_id = self._remove_brackets(experiment.protocol_id)
            protocol = [protocol for protocol in protocols
                        if protocol.protocol_id == experiment.protocol_id]

            biolector_protocol: BiolectorXTProtocol
            if protocol:
                biolector_protocol = BiolectorXTProtocol(id=protocol[0].protocol_id, name=protocol[0].protocol_name)
            else:
                biolector_protocol = BiolectorXTProtocol(id=experiment.protocol_id, name="")

            biolector_experiments.append(BiolectorXTExperiment(
                id=self._remove_brackets(experiment.experiment_id),
                protocol=biolector_protocol,
                start_time=datetime.fromisoformat(experiment.start_time),
                file_path=experiment.file_path,
                finished=experiment.finished
            ))

        return biolector_experiments

    def _remove_brackets(self, value: str) -> str:
        """Remove the brackets from the value

        :param value: value with brackets
        :type value: str
        :return: value without brackets
        :rtype: str
        """
        return value[1:-1] if value.startswith('{') and value.endswith('}') else value
