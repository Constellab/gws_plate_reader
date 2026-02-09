from gws_plate_reader.biolector_xt_analysis._dashboard_core.biolector_state import BiolectorState


def render_select_biolector_experiment_inputs():
    if not BiolectorState.is_multiple_plates():
        return
