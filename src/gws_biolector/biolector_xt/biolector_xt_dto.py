

from gws_core import BaseModelDTO


class CredentialsDataBiolector(BaseModelDTO):
    """Format of the data for biolector credentials"""
    endpoint_url: str
    secure_channel: bool
