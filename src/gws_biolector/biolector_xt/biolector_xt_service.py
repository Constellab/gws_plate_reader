
import os
from typing import Generator, List

import grpc
from google.protobuf.empty_pb2 import Empty
from google.protobuf.wrappers_pb2 import BoolValue, StringValue
from gws_biolector.biolector_xt.biolector_xt_exception import \
    BiolectorXTConnectException
from gws_biolector.biolector_xt.biolector_xt_service_i import \
    BiolectorXTServiceI
from gws_biolector.biolector_xt.biolector_xt_types import \
    CredentialsDataBiolector
from gws_biolector.biolector_xt.grpc.biolectorxtremotecontrol_pb2 import (
    ContinueProtocolResponse, ExperimentInfo, FileChunk, MetaData,
    ProtocolInfo, StartProtocolResponse, StatusUpdateStreamResponse,
    StdResponse, StopProtocolResponse)
from gws_biolector.biolector_xt.grpc.biolectorxtremotecontrol_pb2_grpc import \
    BioLectorXtRemoteControlStub
from gws_core import FileHelper, MessageDispatcher, Settings


class BiolectorXTGrpcChannel():
    """Class to handle generic gRPC channel exceptions
    """

    endpoint: str
    channel: grpc.Channel

    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.channel = grpc.insecure_channel(endpoint)

    def __enter__(self):
        return self.channel.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        result = self.channel.__exit__(exc_type, exc_val, exc_tb)
        if isinstance(exc_val, grpc._channel._InactiveRpcError):
            raise BiolectorXTConnectException()

        return result


class BiolectorXTService(BiolectorXTServiceI):
    """Service to interact with the Biolector XT device using gRPC
    """

    _credentials: CredentialsDataBiolector

    timeout = 20

    def __init__(self, credentials: CredentialsDataBiolector,
                 message_dispatcher: MessageDispatcher = None) -> None:
        super().__init__(message_dispatcher)
        self._credentials = credentials

    def get_protocols(self) -> List[ProtocolInfo]:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.GetProtocols(Empty(), timeout=self.timeout).protocols

    def get_experiments(self) -> List[ExperimentInfo]:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.GetExperimentList(Empty(), timeout=self.timeout).experiment

    def upload_protocol(self, file_path: str) -> StdResponse:
        if not FileHelper.exists_on_os(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)

            return stub.UploadProtocol(self._upload_protocol_chunker(file_path), timeout=self.timeout)

    def _upload_protocol_chunker(self, file_path: str) -> Generator:
        """
        helper function to chop up a local file to smaller chunks that can be send via gRPC
        """
        meta_data = MetaData(filename=file_path)
        chunk_size = 50000  # maximum chunk size 131071
        chunk_list = []
        byte_array = []
        with open(file_path, "rb") as binary_file:
            byte = binary_file.read(chunk_size)
            while byte:
                byte_array.append(byte)
                byte = binary_file.read(chunk_size)

            # Send the file name first
            file_chunk = FileChunk(
                metadata=meta_data
            )
            yield file_chunk

            for chunk in byte_array:
                # send the data chunks
                file_chunk = FileChunk(
                    chunk_data=chunk
                )
                chunk_list.append(file_chunk)
                yield file_chunk

    def start_protocol(self, protocol_id: str) -> StartProtocolResponse:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.StartProtocol(StringValue(value=protocol_id), timeout=self.timeout)

    def stop_current_protocol(self) -> StopProtocolResponse:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.StopProtocol(Empty(), timeout=self.timeout)

    def pause_current_protocol(self) -> None:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.PauseProtocol(BoolValue(value=True), timeout=self.timeout)

    def resume_current_protocol(self) -> ContinueProtocolResponse:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.ContinueProtocol(Empty(), timeout=self.timeout)

    def download_experiment(self, experiment_id: str) -> str:
        """Download the experiment as a zip file and return the path to the file

        :param experiment_id: id of the experiment to download
        :type experiment_id: str
        :return: path to the downloaded file
        :rtype: str
        """
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            response = stub.DownloadExperiment(StringValue(value=experiment_id), timeout=self.timeout)

            tmp_dir = Settings.make_temp_dir()
            file_path = os.path.join(tmp_dir, f"{experiment_id}.zip")

            try:
                with open(file_path, "wb") as file:
                    for chunk in response:
                        file.write(chunk.chunk_data)
            except Exception as e:
                raise Exception(
                    f"Error during the download of biolector experiment. Error : '{e.details()}'. Status : '{e.code().name}'")

            return file_path

    def get_status_update_stream(self) -> StatusUpdateStreamResponse:
        with self.get_grpc_channel() as channel:
            stub = BioLectorXtRemoteControlStub(channel)
            return stub.StatusUpdateStream(Empty(), timeout=self.timeout)

    def get_grpc_channel(self) -> BiolectorXTGrpcChannel:
        return BiolectorXTGrpcChannel(self._credentials.endpoint_url)
