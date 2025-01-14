

from datetime import datetime

from gws_core import BaseModelDTO


class CredentialsDataBiolector(BaseModelDTO):
    """Format of the data for biolector credentials"""
    endpoint_url: str
    secure_channel: bool


class BiolectorXTProtocol(BaseModelDTO):
    """Format of the data for biolector experiment"""
    id: str
    name: str


class BiolectorXTExperiment(BaseModelDTO):
    """Format of the data for biolector experiment"""
    id: str
    protocol: BiolectorXTProtocol
    start_time: datetime
    file_path: str
    finished: bool
