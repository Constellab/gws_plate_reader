import json

import requests
from gws_core import BaseTestCase

from gws_biolector.biolector_xt.biolector_xt_dto import \
    CredentialsDataBiolector
from gws_biolector.biolector_xt.biolector_xt_service import BiolectorXTService


class TestBiolector(BaseTestCase):

    def test_connection(self):
        host = "172.16.102.203"
        port = 50051

    # Define the URL
        http_url = "http://" + host + "/"

        grpc_url = host + ":" + str(port)
        final_json = {
            'http_url': http_url,
            'grpc_url': grpc_url
        }

        ############################### HTTP TEST ###############################
        try:
            # Make the HTTP GET request
            response = requests.get(http_url, timeout=5)
            final_json['http_status'] = True
            final_json['http_response'] = str(response.status_code) + ' ' + response.text
        except Exception as e:
            final_json['http_status'] = False
            final_json['http_response'] = str(e)

        ############################### TEST GET PROTOCOL ###############################

        credentials = CredentialsDataBiolector(endpoint_url=grpc_url, secure_channel=False)
        service = BiolectorXTService(credentials)
        try:
            protocols = service.get_protocols()
            final_json['protocol_status'] = True
            final_json['protocol_response'] = str(protocols)
        except Exception as e:
            final_json['protocol_status'] = False
            final_json['protocol_response'] = str(e)

        ############################### TEST GET EXPERIMENTS ###############################

        try:
            experiment = service.get_experiments()
            final_json['exp_status'] = True
            final_json['exp_response'] = str(experiment)
        except Exception as e:
            final_json['exp_status'] = False
            final_json['exp_response'] = str(e)

        ############################### RETURN RESULT ###############################

        print(json.dumps(final_json))
