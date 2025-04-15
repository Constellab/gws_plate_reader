from typing import Dict, List

import pandas as pd
import streamlit as st
from gws_core.impl.table.table import Table
from gws_core.resource.resource_model import ResourceModel
from gws_core.streamlit import StreamlitContainers, StreamlitResourceSelect
from gws_core.tag.tag import Tag
from gws_plate_reader.biolector_xt_analysis.biolector_state import \
    BiolectorExperiment


def add_experiment_to_experiments_list(r: ResourceModel) -> Dict[str, "BiolectorExperimentWithDetails"]:
    experiments_list: Dict[str, BiolectorExperimentWithDetails] = st.session_state.get('experiments_list', {})

    list_raw_data_id_biolector_experiment = [(e.raw_data, e.id_biolector_experiment) for e in experiments_list.values()]
    table = r.get_resource()
    if table is not None:
        table.name = r.get_entity_name()
        raw_data = table.tags.get_by_key("raw_data")[0].value
        id_biolector_experiment = table.tags.get_by_key("name")[0].value
        if '-' in id_biolector_experiment:
            raise ValueError(
                f"Experiment name {id_biolector_experiment} contains '-' character. "
                f"Please rename the experiment.")
        if '-' in raw_data:
            raise ValueError(
                f"Raw data {raw_data} contains '-' character. "
                f"Please rename the raw data.")
        # num = number of element in list_id_biolector_experiment when split by '-' [0] matches the first part of the name
        num = len([i
                   for i in list_raw_data_id_biolector_experiment
                   if i[0].split('-')[0] == raw_data and i[1].split('-')[0] == id_biolector_experiment])
        num_raw_data = len([i for i in list_raw_data_id_biolector_experiment
                            if i[0].split('-')[0] == raw_data])
        if num_raw_data > 0 and num == 0:
            raw_data = f"{raw_data}-{num_raw_data+1}"

        if num > 0:
            id_biolector_experiment = f"{id_biolector_experiment}-{num+1}"

        list_raw_data_id_biolector_experiment.append((raw_data, id_biolector_experiment))
        experiment = BiolectorExperimentWithDetails(
            table, raw_data, id_biolector_experiment)
        experiments_list[f"{raw_data}-{id_biolector_experiment}"] = experiment
    st.session_state['experiments_list'] = experiments_list
    return experiments_list


def render_find_experiments_page():
    st.title('Find experiments')
    if 'selected_resources' in st.session_state:
        selected_resources = st.session_state['selected_resources']
    else:
        selected_resources = []
    resource_select = StreamlitResourceSelect()
    selected_resource = resource_select.select_resource(
        placeholder='Search for resource', key="resource-selector", defaut_resource=None, default_filters={
            'tags': [{
                'key': 'origin',
                'value': 'biolector_dashboard'
            }, {
                'key': 'raw_data'
            }]
        })

    if selected_resource:
        if selected_resource not in selected_resources:
            selected_resources.append(selected_resource)
            st.session_state['selected_resources'] = selected_resources
            add_experiment_to_experiments_list(selected_resource)

    if len(selected_resources) > 0:
        experiments_list: Dict[str, BiolectorExperimentWithDetails] = st.session_state.get('experiments_list', None)
        if experiments_list is None:
            st.error('No experiments found')
            return
        experiments_list_dict = [experiment.to_detail_dict() for experiment in experiments_list.values()]
        experiments_list_df = pd.DataFrame(experiments_list_dict)

        with StreamlitContainers.full_width_dataframe_container(key="experiments_list_container"):
            experiments_df = st.data_editor(
                experiments_list_df,
                column_config={
                    "selected": st.column_config.CheckboxColumn(
                        default=False
                    )
                },
                disabled=['id_biolector_experiment', 'raw_data', 'filter', 'wells', 'user', 'comment'],
                hide_index=True,
                use_container_width=True
            )

        selected_experiments = {}
        selected_expermiments_indexes = experiments_df.index[experiments_df['selected']].tolist()
        selected_experiments_df = experiments_df.iloc[selected_expermiments_indexes]
        for experiment_id, experiment in experiments_list.items():
            count_selected_experiments_matching = len(
                selected_experiments_df
                [(selected_experiments_df['id_biolector_experiment'] == experiment.id_biolector_experiment) &
                    (selected_experiments_df['raw_data'] == experiment.raw_data)])
            if count_selected_experiments_matching == 1:
                experiment.set_selected(True)
                selected_experiments[experiment_id] = experiment
            elif count_selected_experiments_matching > 1:
                st.error(
                    f"Experiment {experiment_id} is present {count_selected_experiments_matching} times in the selected experiments")
            else:
                experiment.set_selected(False)

        if st.button('Add selected experiments', key='add_selected_experiments_button',
                     disabled=(len(selected_experiments.keys()) == 0
                               or (
                                   st.session_state.get('selected_experiments', None)
                                   is not None and st.session_state['selected_experiments'].keys() ==
                                   selected_experiments.keys()))):
            st.session_state['experiments_list'] = experiments_list
            st.session_state['selected_experiments'] = selected_experiments
            st.rerun()
    else:
        st.info('No resource selected')


class BiolectorExperimentWithDetails(BiolectorExperiment):

    wells: List[str]
    user: str
    comment: str
    selected: bool

    def __init__(self, table: Table, raw_data: str, id_biolector_experiment: str):
        self.id_biolector_experiment = id_biolector_experiment
        self.raw_data = raw_data
        self.filter = table.tags.get_by_key("filter")[0].value

        base_biolector_experiment = BiolectorExperiment.from_table(
            table, self.filter, raw_data, id_biolector_experiment)

        # Add other infos
        self.wells = list(base_biolector_experiment.metadata.keys())
        self.user = table.tags.get_by_key("user_name")[0].value
        self.comment = table.tags.get_by_key("comment")[0].value
        self.selected = False

        # rename data columns by adding the '_' + raw_data, if the column is not 'time' or 'Temps_en_h'
        base_biolector_experiment.data.rename(
            columns={col: f'{col}_{raw_data}'
                     for col in base_biolector_experiment.data.columns
                     if col not in ['time', 'Temps_en_h']},
            inplace=True)
        self.data = base_biolector_experiment.data

        # rename metadata keys by adding the '_' + id_biolector_experiment, if the key is not 'time' or 'Temps_en_h'
        self.metadata = {}
        for well, metadata in base_biolector_experiment.metadata.items():
            self.metadata[well] = {raw_data: metadata}

    def to_detail_dict(self) -> Dict:
        return {
            'selected': self.selected,
            'id_biolector_experiment': self.id_biolector_experiment,
            'raw_data': self.raw_data,
            'filter': self.filter,
            'wells': self.wells,
            'user': self.user,
            'comment': self.comment
        }

    def set_selected(self, selected: bool):
        self.selected = selected
