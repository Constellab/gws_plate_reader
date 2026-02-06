import json
import os

from gws_core import FileDownloader, Settings

from gws_plate_reader.biolector_xt.biolector_xt_service_i import BiolectorXTServiceI
from gws_plate_reader.biolector_xt.grpc.biolectorxtremotecontrol_pb2 import (
    ContinueProtocolResponse,
    ExperimentInfo,
    ProtocolInfo,
    StartProtocolResponse,
    StatusUpdateStreamResponse,
    StdResponse,
    StopProtocolResponse,
)


class BiolectorXTMockService(BiolectorXTServiceI):
    """Service to simulate the interaction with the Biolector XT device using gRPC"""

    PROTOCOL_LIST = "protocol_list.json"
    EXPERIMENT_LIST = "experiment_list.json"
    EXPERIMENT_ZIP_LOCATION = "https://storage.gra.cloud.ovh.net/v1/AUTH_a0286631d7b24afba3f3cdebed2992aa/opendata/gws_plate_reader/Biolector_xt_example_data.zip"

    def get_protocols(self) -> list[ProtocolInfo]:
        protocol_infos = self._read_json_file(
            os.path.join(self._get_data_folder(), self.PROTOCOL_LIST)
        )

        protocol_infos_list = []
        for protocol_info in protocol_infos:
            protocol_infos_list.append(
                ProtocolInfo(
                    protocol_id=protocol_info["protocol_id"],
                    protocol_name=protocol_info["protocol_name"],
                )
            )

        return protocol_infos_list

    def get_experiments(self) -> list[ExperimentInfo]:
        experiment_infos = self._read_json_file(
            os.path.join(self._get_data_folder(), self.EXPERIMENT_LIST)
        )
        experiment_infos_list = []
        for experiment_info in experiment_infos:
            experiment_infos_list.append(
                ExperimentInfo(
                    experiment_id=experiment_info["experiment_id"],
                    protocol_id=experiment_info["protocol_id"],
                    start_time=experiment_info["start_time"],
                    file_path=experiment_info["file_path"],
                    finished=experiment_info["finished"],
                )
            )

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
        dest_folder = os.path.join(Settings.make_temp_dir())
        downloader = FileDownloader(dest_folder, self.message_dispatcher)

        dest_file = os.path.join(dest_folder, "experiment.zip")

        return downloader.download_file_if_missing(self.EXPERIMENT_ZIP_LOCATION, dest_file)

    def get_status_update_stream(self) -> StatusUpdateStreamResponse:
        pass

    def _read_json_file(self, file_path: str) -> dict:
        with open(file_path, encoding="utf-8") as file:
            return json.load(file)

    def _get_data_folder(self) -> str:
        return Settings.get_instance().get_variable("gws_plate_reader", "data_dir")
