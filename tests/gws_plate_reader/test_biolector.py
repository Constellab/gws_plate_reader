import json

from google.protobuf.json_format import MessageToJson
from gws_core import BaseTestCase
from gws_plate_reader.biolector_xt.biolector_xt_service import \
    BiolectorXTService
from gws_plate_reader.biolector_xt.biolector_xt_types import \
    CredentialsDataBiolector


class TestBiolector(BaseTestCase):

    def test_connection(self):
        host = "172.16.102.203"
        port = 50051

        grpc_url = host + ":" + str(port)
        final_json = {
            'grpc_url': grpc_url
        }

        ############################### TEST GET PROTOCOL ###############################

        credentials = CredentialsDataBiolector(endpoint_url=grpc_url, secure_channel=False)
        service = BiolectorXTService(credentials)
        try:
            protocols = service.get_protocols()
            final_json['protocol_status'] = True
            final_json['protocol_response'] = json.dumps(protocols[0].to_dict())
        except Exception as e:
            final_json['protocol_status'] = False
            final_json['protocol_response'] = str(e)

        ############################### TEST GET EXPERIMENTS ###############################

        try:
            experiment = service.get_experiments()
            final_json['exp_status'] = True
            final_json['exp_response'] = json.dumps(experiment)
        except Exception as e:
            final_json['exp_status'] = False
            final_json['exp_response'] = str(e)

        ############################### RETURN RESULT ###############################

        print(json.dumps(final_json))
