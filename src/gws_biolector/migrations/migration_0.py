
from gws_biolector.biolector_xt.tasks.biolector_dashboard import (
    BiolectorDashboard, BiolectorDashboardClass)
from gws_biolector.biolector_xt_parser.dashboard.parser_dashboard import (
    ParserDashboard, ParserDashboardClass)
from gws_biolector.biolector_xt_parser.standalone_parser_dashboard.standalone_parser_dashboard import (
    BiolectorParserStandalone, BiolectorParserStandaloneClass)
from gws_core import (BrickMigration, StreamlitResource, Version,
                      brick_migration)


@brick_migration('0.5.4', short_description='Migrate dashboard resources')
class Migration054(BrickMigration):

    @classmethod
    def migrate(cls, from_version: Version, to_version: Version) -> None:

        StreamlitResource.migrate_streamlit_resources(BiolectorDashboard.get_typing_name(),
                                                      BiolectorDashboardClass.get_typing_name())

        StreamlitResource.migrate_streamlit_resources(ParserDashboard.get_typing_name(),
                                                      ParserDashboardClass.get_typing_name())

        StreamlitResource.migrate_streamlit_resources(BiolectorParserStandalone.get_typing_name(),
                                                      BiolectorParserStandaloneClass.get_typing_name())
