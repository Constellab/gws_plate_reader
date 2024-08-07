
import json
import os
import shutil
from time import sleep
from typing import List

from gws_core import FileHelper, Settings

from gws_biolector.biolector_xt.biolector_xt_service_i import \
    BiolectorXTServiceI
from gws_biolector.biolector_xt.grpc.biolectorxtremotecontrol_pb2 import (
    ContinueProtocolResponse, ExperimentInfo, ProtocolInfo,
    StartProtocolResponse, StatusUpdateStreamResponse, StdResponse,
    StopProtocolResponse)


class BiolectorXTMockService(BiolectorXTServiceI):
    """Service to simulate the interaction with the Biolector XT device using gRPC
    """

    # TODO TO SET DYANMICALLY
    data_folder = '/lab/user/bricks/gws_biolector/data'

    def get_protocols(self) -> List[ProtocolInfo]:

        protocol_infos = self._read_json_file(os.path.join(self.data_folder, 'protocol_list.json'))

        protocol_infos_list = []
        for protocol_info in protocol_infos:
            protocol_infos_list.append(ProtocolInfo(
                protocol_id=protocol_info["protocol_id"],
                protocol_name=protocol_info["protocol_name"]
            ))

        return protocol_infos_list

    def get_experiments(self) -> List[ExperimentInfo]:

        experiment_infos = self._read_json_file(os.path.join(self.data_folder, 'experiment_list.json'))
        experiment_infos_list = []
        for experiment_info in experiment_infos:
            experiment_infos_list.append(ExperimentInfo(
                experiment_id=experiment_info["experiment_id"],
                protocol_id=experiment_info["protocol_id"],
                start_time=experiment_info["start_time"],
                file_path=experiment_info["file_path"],
                finished=experiment_info["finished"]
            ))

        return experiment_infos_list

    def upload_protocol(self, file_path: str) -> StdResponse:
        pass

    def start_protocol(self, protocol_id: str) -> StartProtocolResponse:
        pass

    def stop_current_protocol(self) -> StopProtocolResponse:
        pass

    def pause_current_protocol(self) -> None:
        pass

    def resume_current_protocol(self) -> ContinueProtocolResponse:
        pass

    def download_experiment(self, experiment_id: str) -> str:
        tmp_dir = Settings.make_temp_dir()

        # copy the directory content to the temp dir
        shutil.copytree(os.path.join(self.data_folder, 'experiment_example'), tmp_dir, dirs_exist_ok=True)
        print(f"Experiment downloaded to: {tmp_dir}")

        return tmp_dir

    def get_status_update_stream(self) -> StatusUpdateStreamResponse:
        pass

    def _read_json_file(self, file_path: str) -> dict:
        with open(file_path, 'r', encoding='utf-8') as file:
            return json.load(file)
