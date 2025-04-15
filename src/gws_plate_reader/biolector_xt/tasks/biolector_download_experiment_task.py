

import os

from gws_core import (BoolParam, ConfigParams, ConfigSpecs,
                      CredentialsDataOther, CredentialsParam, CredentialsType,
                      File, FileHelper, Folder, InputSpecs, OutputSpec,
                      OutputSpecs, StrParam, Table, TableImporter, Task,
                      TaskInputs, TaskOutputs, TypingStyle, ZipCompress,
                      task_decorator)
from gws_plate_reader.biolector_xt.biolector_xt_mock_service import \
    BiolectorXTMockService
from gws_plate_reader.biolector_xt.biolector_xt_service import \
    BiolectorXTService
from gws_plate_reader.biolector_xt.biolector_xt_service_i import \
    BiolectorXTServiceI
from gws_plate_reader.biolector_xt.biolector_xt_types import \
    CredentialsDataBiolector


@task_decorator(unique_name="BiolectorDownloadExperiment",
                short_description="Download the reuslt of an experiment from Biolector XT",
                style=TypingStyle.community_icon("bioreactor"))
class BiolectorDownloadExperiment(Task):

    config_specs: ConfigSpecs = ConfigSpecs({
        'experiment_id': StrParam(human_name="Experiment ID",
                                  short_description="The ID of the BiolectorXT experiment to download"),
        'credentials': CredentialsParam(credentials_type=CredentialsType.OTHER),
        'mock_service': BoolParam(human_name="Mock Service",
                                  short_description="Use the mock service to simulate the interaction with Biolector XT",
                                  default_value=False, visibility="private")
    })
    input_specs: InputSpecs = InputSpecs()
    output_specs: OutputSpecs = OutputSpecs({
        'result': OutputSpec(Table, human_name="Result Table",
                             short_description="The result of the experiment in a table format"),
        'raw_data': OutputSpec(Folder, human_name="Raw Data Folder",
                               short_description="The unzipped raw data of the experiment")
    })

    zip_path = None

    def run(self, params: ConfigParams, inputs: TaskInputs) -> TaskOutputs:
        # Get the experiment ID
        experiment_id: str = params.get_value('experiment_id')
        experiment_id = experiment_id.strip()

        # Set { at the beginning and } at the end of the experiment ID if not present
        if not experiment_id.startswith('{'):
            self.log_info_message("Adding missing '{' at the beginning of the experiment ID")
            experiment_id = '{' + experiment_id

        if not experiment_id.endswith('}'):
            self.log_info_message("Adding missing '}' at the end of the experiment ID")
            experiment_id = experiment_id + '}'

        service = self.get_service(params.get_value('credentials'), params.get_value('mock_service'))

        # download experiment
        self.log_info_message(f"Downloading experiment {experiment_id} from Biolector XT")
        self.zip_path = service.download_experiment(experiment_id)

        # unzip the file
        self.log_info_message("Unzipping the downloaded file")
        tmp_dir = self.create_tmp_dir()
        ZipCompress.decompress(self.zip_path, tmp_dir)

        # read the csv result file
        # find the csv file in the unzipped folder, no recursion
        csv_file = None
        for file in os.listdir(tmp_dir):
            if file.endswith('.csv'):
                csv_file = os.path.join(tmp_dir, file)
                break

        if csv_file is None:
            raise ValueError("No CSV file found in the downloaded experiment zip file")

        self.log_info_message(f"Importing csv file: {csv_file}")

        table = TableImporter.call(File(csv_file), {
            'file_format': 'csv',
            'delimiter': ';',
            'header': 0,
            'format_header_names': True,
            'index_column': -1,
        })

        folder = Folder(tmp_dir)
        folder.name = f"Biolector raw data {experiment_id}"
        return {'result': table, 'raw_data': folder}

    def run_after_task(self) -> None:
        super().run_after_task()
        if self.zip_path:
            FileHelper.delete_file(self.zip_path)

    def get_service(self, credentials: CredentialsDataOther, mock_service: bool) -> BiolectorXTServiceI:
        if mock_service:
            return BiolectorXTMockService(self.message_dispatcher)
        else:
            try:
                biolector_credentials = CredentialsDataBiolector.from_json(credentials.data)
            except Exception as e:
                raise ValueError("Invalid credentials data: " + str(e))
            return BiolectorXTService(biolector_credentials, self.message_dispatcher)
