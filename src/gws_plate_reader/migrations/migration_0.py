
from gws_core import (BrickMigration, StreamlitResource, Version,
                      brick_migration)
from gws_plate_reader.biolector_xt.tasks.biolector_dashboard import (
    BiolectorDashboard, BiolectorDashboardClass)
from gws_plate_reader.biolector_xt_analysis.dashboard.analysis_dashboard import (
    AnalysisDashboard, AnalysisDashboardClass)
from gws_plate_reader.biolector_xt_analysis.standalone_analysis_dashboard.standalone_analysis_dashboard import (
    BiolectorParserStandalone, BiolectorParserStandaloneClass)


@brick_migration('0.5.4', short_description='Migrate dashboard resources')
class Migration054(BrickMigration):

    @classmethod
    def migrate(cls, from_version: Version, to_version: Version) -> None:

        StreamlitResource.migrate_streamlit_resources(BiolectorDashboard.get_typing_name(),
                                                      BiolectorDashboardClass.get_typing_name())

        StreamlitResource.migrate_streamlit_resources(AnalysisDashboard.get_typing_name(),
                                                      AnalysisDashboardClass.get_typing_name())

        StreamlitResource.migrate_streamlit_resources(BiolectorParserStandalone.get_typing_name(),
                                                      BiolectorParserStandaloneClass.get_typing_name())
