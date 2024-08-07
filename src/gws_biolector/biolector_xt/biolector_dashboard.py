

import os

from gws_core.config.config_params import ConfigParams
from gws_core.config.config_types import ConfigSpecs
from gws_core.core.utils.compress.zip_compress import ZipCompress
from gws_core.credentials.credentials_param import CredentialsParam
from gws_core.credentials.credentials_type import CredentialsType
from gws_core.external_source.biolector_xt.biolector_xt_dto import \
    CredentialsDataBiolector
from gws_core.impl.file.file import File
from gws_core.impl.file.file_helper import FileHelper
from gws_core.impl.table.tasks.table_importer import TableImporter
from gws_core.io.io_spec import InputSpec, OutputSpec
from gws_core.io.io_specs import InputSpecs, OutputSpecs
from gws_core.model.typing_style import TypingStyle
from gws_core.streamlit.streamlit_resource import StreamlitResource
from gws_core.task.task import Task
from gws_core.task.task_decorator import task_decorator
from gws_core.task.task_io import TaskInputs, TaskOutputs


@task_decorator(unique_name="BiolectorDownloadExperiment",
                short_description="Download the reuslt of an experiment from Biolector XT",
                style=TypingStyle.community_icon("bioreactor"), hide=True)
class BiolectorDownloadExperiment(Task):

    config_specs: ConfigSpecs = {
        'credentials': CredentialsParam(credentials_type=CredentialsType.OTHER),
    }

    output_specs: OutputSpecs = OutputSpecs({'dashboard': OutputSpec(StreamlitResource)})


    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:

        biolector_credentials: CredentialsDataBiolector
        try:
            biolector_credentials = CredentialsDataBiolector.from_json(params.get_value('credentials'))
        except Exception as e:
            raise ValueError("Invalid credentials data: " + str(e))
        

        streamlit_resource = StreamlitResource()

        streamlit_resource.

        
        return {'result': table}

