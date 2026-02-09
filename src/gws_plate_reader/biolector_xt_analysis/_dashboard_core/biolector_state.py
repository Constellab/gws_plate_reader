from enum import Enum
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from gws_core.impl.table.table import Table
from gws_core.tag.tag import Tag
from pandas import DataFrame

CROSSED_OUT_WELLS = [f"{chr(65 + row)}{col + 1:02d}" for row in range(2)
                     for col in range(8)]
ALL_WELLS = [f"{chr(65 + row)}{col + 1:02d}" for row in range(6)
             for col in range(8)]


class BiolectorExperiment():
    metadata: Dict = None
    data: DataFrame = None
    filter: str
    id_biolector_experiment: Optional[str] = None
    raw_data: Optional[str] = None

    def __init__(
            self, metadata: Dict, data: DataFrame, filter: str, raw_data: Optional[str] = None,
            id_biolector_experiment: Optional[str] = None):
        self.metadata = metadata
        self.data = data
        self.raw_data = raw_data
        self.id_biolector_experiment = id_biolector_experiment
        self.filter = filter

    @classmethod
    def from_table(cls, table: Table, filter: str, raw_data: Optional[str] = None,
                   id_biolector_experiment: Optional[str] = None) -> "BiolectorExperiment":
        data = table.to_dataframe()
        metadata = {}
        for column_info in table.get_columns_info():
            if column_info['name'] not in ['time', 'Temps_en_h']:
                tags = column_info['tags']
                if 'well' in tags:
                    del tags['well']
                metadata[column_info['name']] = tags

        # drop columns with all NaN values if col in CROSSED_OUT_WELLS
        data = data.drop(
            columns=[col for col in data.columns if col in CROSSED_OUT_WELLS and data[col].isna().all()],
            errors='ignore')
        return cls(metadata, data, filter, raw_data, id_biolector_experiment)


class BiolectorStateMode(Enum):
    SINGLE_PLATE = "single_plate"
    MULTIPLE_PLATES = "multiple_plates"
    STANDALONE = "standalone"


class BiolectorState():

    IS_BIOLECTOR_STATE_INIT_KEY = "is_biolector_state_init"
    BASE_DATA_KEY = "base_data"
    DATA_KEY = "data"
    BIOLECTOR_STATE_MODE_KEY = "biolector_state_mode"
    PLATE_LAYOUT_KEY = "plate_layout"
    ALL_KEYS_WELL_DESCRIPTION_KEY = "all_keys_well_description"
    SELECTED_ROWS_KEY = "selected_rows"
    SELECTED_COLS_KEY = "selected_cols"
    WELLS_CLICKED_KEY = 'wells_clicked'
    SELECTED_REPLICATES_WELLS_KEY = 'selected_replicates_wells'
    FILTERS_LIST_KEY = 'filters_list'
    SELECTED_FILTERS_KEY = 'selected_filters'
    INPUT_TAG_KEY = 'input_tag'
    CURRENT_REPLICATE_MODE_KEY = 'current_replicate_mode'
    REPLICATES_SAVED_KEY = 'replicates_saved'
    OPTIONS_REPLICATES = 'options_replicates'
    REPLICATED_WELLS_SHOW_KEY = 'replicated_wells_show'
    WELLS_TO_SHOW_KEY = 'wells_to_show'
    STATS_FOLDER_KEY = 'stats_folder'
    PNG_METADATA_KEY = 'png_metadata'
    PLOT_MODE_KEY = 'plot_mode_saved'
    PLOT_TIME_KEY = 'plot_time_saved'
    ERROR_BAND_KEY = 'error_band_saved'
    SUCCESS_MESSAGE_RESOURCE_TABLE_KEY = 'success_message_resource_table'

    @classmethod
    def init(
            cls, data: Dict[str, Any], mode: BiolectorStateMode = BiolectorStateMode.SINGLE_PLATE,
            input_tag: Tag = None):
        st.session_state[cls.BIOLECTOR_STATE_MODE_KEY] = mode

        if not cls.is_same_base_data(data) and cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES and cls.DATA_KEY in st.session_state:
            cls.init_session_state()
        st.session_state[cls.DATA_KEY] = cls.get_data(data)
        st.session_state[cls.INPUT_TAG_KEY] = input_tag if input_tag else None
        st.session_state[cls.IS_BIOLECTOR_STATE_INIT_KEY] = True

    @classmethod
    def init_session_state(cls):
        """
        Set to None all the session state keys that are params of the class.
        """
        if cls.IS_BIOLECTOR_STATE_INIT_KEY in st.session_state:
            del st.session_state[cls.IS_BIOLECTOR_STATE_INIT_KEY]
        if cls.DATA_KEY in st.session_state:
            del st.session_state[cls.DATA_KEY]
        if cls.PLATE_LAYOUT_KEY in st.session_state:
            del st.session_state[cls.PLATE_LAYOUT_KEY]
        if cls.ALL_KEYS_WELL_DESCRIPTION_KEY in st.session_state:
            del st.session_state[cls.ALL_KEYS_WELL_DESCRIPTION_KEY]
        if cls.SELECTED_ROWS_KEY in st.session_state:
            del st.session_state[cls.SELECTED_ROWS_KEY]
        if cls.SELECTED_COLS_KEY in st.session_state:
            del st.session_state[cls.SELECTED_COLS_KEY]
        if cls.WELLS_CLICKED_KEY in st.session_state:
            del st.session_state[cls.WELLS_CLICKED_KEY]
        if cls.SELECTED_REPLICATES_WELLS_KEY in st.session_state:
            del st.session_state[cls.SELECTED_REPLICATES_WELLS_KEY]
        if cls.FILTERS_LIST_KEY in st.session_state:
            del st.session_state[cls.FILTERS_LIST_KEY]
        if cls.SELECTED_FILTERS_KEY in st.session_state:
            del st.session_state[cls.SELECTED_FILTERS_KEY]
        if cls.INPUT_TAG_KEY in st.session_state:
            del st.session_state[cls.INPUT_TAG_KEY]
        if cls.CURRENT_REPLICATE_MODE_KEY in st.session_state:
            del st.session_state[cls.CURRENT_REPLICATE_MODE_KEY]
        if cls.REPLICATES_SAVED_KEY in st.session_state:
            del st.session_state[cls.REPLICATES_SAVED_KEY]
        if cls.OPTIONS_REPLICATES in st.session_state:
            del st.session_state[cls.OPTIONS_REPLICATES]
        if cls.REPLICATED_WELLS_SHOW_KEY in st.session_state:
            del st.session_state[cls.REPLICATED_WELLS_SHOW_KEY]
        if cls.WELLS_TO_SHOW_KEY in st.session_state:
            del st.session_state[cls.WELLS_TO_SHOW_KEY]

    @classmethod
    def is_init(cls) -> bool:
        """
        Check if the Biolector state is initialized.
        """
        return st.session_state.get(cls.IS_BIOLECTOR_STATE_INIT_KEY, False)

    @classmethod
    def get_mode(cls) -> BiolectorStateMode:
        """
        Get the mode of the Biolector state.
        """
        if cls.BIOLECTOR_STATE_MODE_KEY not in st.session_state:
            raise KeyError(f"Key '{cls.BIOLECTOR_STATE_MODE_KEY}' not found in session state.")
        return st.session_state.get(cls.BIOLECTOR_STATE_MODE_KEY, None)

    @classmethod
    def is_single_plate(cls) -> bool:
        """
        Check if the mode is single plate.
        """
        return cls.get_mode() == BiolectorStateMode.SINGLE_PLATE

    @classmethod
    def is_standalone(cls) -> bool:
        """
        Check if the mode is standalone.
        """
        return cls.get_mode() == BiolectorStateMode.STANDALONE

    @classmethod
    def is_multiple_plates(cls) -> bool:
        """
        Check if the mode is multiple plates.
        """
        return cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES

    @classmethod
    def get_input_tag(cls) -> Optional[Tag]:  # TODO : check if it is a list
        """
        Get the input tag from the session state.
        """
        if cls.INPUT_TAG_KEY not in st.session_state:
            raise KeyError(f"Key '{cls.INPUT_TAG_KEY}' not found in session state.")
        return st.session_state.get(cls.INPUT_TAG_KEY, None)

    @classmethod
    def is_microfluidics(cls) -> bool:
        """
        Check if the mode is microfluidics.
        """
        data = cls.get_data()
        for key, biolector_experiment in data.items():
            if 'A01' in biolector_experiment.data.columns:
                return False
        return True

    @classmethod
    def is_same_base_data(cls, data: Dict[str, Any]) -> bool:
        """
        Get the wells clicked from the session state.
        """
        base_data = None
        if cls.BASE_DATA_KEY in st.session_state:
            base_data = st.session_state.get(cls.BASE_DATA_KEY, None)

        return base_data is None or data is None or base_data == data

    ###################################### DATA #######################################
    @classmethod
    def get_data(cls, data: Dict[str, Any] = None) -> Dict[str, BiolectorExperiment]:
        """
        Get the data from the session state.
        """

        if cls.DATA_KEY in st.session_state and cls.is_same_base_data(data):
            return st.session_state.get(cls.DATA_KEY, None)

        if data is None:
            raise ValueError("Data is None. Please provide data to set.")

        st.session_state[cls.BASE_DATA_KEY] = data
        if cls.get_mode() == BiolectorStateMode.SINGLE_PLATE or cls.get_mode() == BiolectorStateMode.STANDALONE:
            return cls._set_single_plate_data(data)
        else:
            return cls._set_multiple_plates_data(data)

    @classmethod
    def _set_single_plate_data(cls, data: Dict[str, Table]) -> Dict[str, BiolectorExperiment]:
        """
        Get the single plate data from the session state.
        """
        for key, table in data.items():
            biolector_experiment = BiolectorExperiment.from_table(table, key)
            data[key] = biolector_experiment
        st.session_state[cls.DATA_KEY] = data
        return data

    @classmethod
    def _set_multiple_plates_data(cls, data_: Dict[str, BiolectorExperiment]) -> Dict[str, BiolectorExperiment]:
        """
        Get the multiple plates data from the session state.
        """
        grouped_data: Dict[str, List[BiolectorExperiment]] = {}
        data: Dict[str, BiolectorExperiment] = {}
        for key, experiment in data_.items():
            if experiment.id_biolector_experiment is None:
                raise ValueError("Experiment id_biolector is None.")
            if experiment.filter not in grouped_data:
                grouped_data[experiment.filter] = []
            grouped_data[experiment.filter].append(experiment)
        for filter_, experiments in grouped_data.items():
            metadata = {}
            for experiment in experiments:
                for well, metadata_ in experiment.metadata.items():
                    if well not in metadata:
                        metadata[well] = {}
                    metadata[well].update(metadata_)
            dataframe = pd.concat([experiment.data for experiment in experiments], ignore_index=True)
            dataframe = dataframe.groupby(['time', 'Temps_en_h'], as_index=False).agg(
                lambda x: next(filter(pd.notna, x), None))
            dataframe = dataframe[['time', 'Temps_en_h'] + sorted(
                [col for col in dataframe.columns if col not in ['time', 'Temps_en_h']])]
            data[filter_] = BiolectorExperiment(metadata=metadata, data=dataframe, filter=filter_)

        st.session_state[cls.DATA_KEY] = data
        return data

    ####################################### WELL DATA DESCRIPTION #######################################

    @classmethod
    def get_all_keys_well_description(cls) -> List[str]:
        """
        Set the all keys well description in the session state.
        """
        if cls.ALL_KEYS_WELL_DESCRIPTION_KEY in st.session_state:
            return st.session_state.get(cls.ALL_KEYS_WELL_DESCRIPTION_KEY, None)

        if cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
            return cls._set_multiple_plates_all_keys_well_description()
        else:
            return cls._set_single_plate_all_keys_well_description()

    @classmethod
    def _set_single_plate_all_keys_well_description(cls) -> List[str]:
        """
        Get the single plate all keys well description from the session state.
        """
        data: Dict[str, BiolectorExperiment] = cls.get_data()
        all_keys_well_description = set()
        for key, biolector_experiment in data.items():
            for metadata_key, metadata in biolector_experiment.metadata.items():
                all_keys_well_description.update(list(metadata.keys()))
        all_keys_well_description = [item for item in all_keys_well_description]
        st.session_state[cls.ALL_KEYS_WELL_DESCRIPTION_KEY] = all_keys_well_description
        return all_keys_well_description

    @classmethod
    def _set_multiple_plates_all_keys_well_description(cls) -> List[str]:
        """
        Get the multiple plates all keys well description from the session state.
        """
        data = cls.get_data()
        all_keys_well_description = set()
        for key, biolector_experiment in data.items():
            for well, plate_metadata in biolector_experiment.metadata.items():
                for plate, metadata in plate_metadata.items():
                    all_keys_well_description.update(list(metadata.keys()))
        all_keys_well_description = [item for item in all_keys_well_description]
        st.session_state[cls.ALL_KEYS_WELL_DESCRIPTION_KEY] = all_keys_well_description
        return all_keys_well_description

    @classmethod
    def get_well_data_description(cls) -> Dict:
        """
        Get the well data description from the session state.
        """
        data_description: Dict[str, str] = {}
        data = cls.get_data()
        for key, biolector_experiment in data.items():
            for well, metadata in biolector_experiment.metadata.items():
                if well not in data_description:
                    data_description[well] = metadata
                else:
                    data_description[well].update(metadata)
                # add columns with all NaN values if col in ALL_WELLS and not in data.columns
        for well in ALL_WELLS:
            if well not in data_description:
                data_description[well] = {}

        return data_description

    ######################################### FILTERS ########################################
    @classmethod
    def get_filters_list(cls) -> List[str]:
        """
        Get the filters list from the session state.
        """
        if cls.FILTERS_LIST_KEY in st.session_state:
            return st.session_state.get(cls.FILTERS_LIST_KEY, [])

        filters_list = set()
        data = cls.get_data()
        for key, biolector_experiment in data.items():
            filters_list.update([biolector_experiment.filter])
        filters_list = list(filters_list)
        st.session_state[cls.FILTERS_LIST_KEY] = filters_list
        return filters_list

    @classmethod
    def get_selected_filters(cls) -> List[str]:
        """
        Get the selected filters from the session state.
        """
        return st.session_state.get(cls.SELECTED_FILTERS_KEY, None)

    @classmethod
    def set_selected_filters(cls, selected_filters: List[str]) -> None:
        """
        Set the selected filters in the session state.
        """
        st.session_state[cls.SELECTED_FILTERS_KEY] = selected_filters

    ######################################## CURRENT REPLICATE MODE ########################################
    @classmethod
    def get_current_replicate_mode(cls) -> str:
        """
        Get the current replicate mode from the session state.
        """
        return st.session_state.get(cls.CURRENT_REPLICATE_MODE_KEY, None)

    @classmethod
    def set_current_replicate_mode(cls, current_replicate_mode: str) -> None:
        """
        Set the current replicate mode in the session state.
        """
        if cls.get_current_replicate_mode() == current_replicate_mode:
            return

        st.session_state[cls.CURRENT_REPLICATE_MODE_KEY] = current_replicate_mode if current_replicate_mode in cls.get_all_keys_well_description() else None

    ######################################## SELECTED WELLS ########################################
    @classmethod
    def get_wells_clicked(cls) -> List[str]:
        """
        Get the clicked wells from the session state.
        """
        return st.session_state.get(cls.WELLS_CLICKED_KEY, [])

    @classmethod
    def append_well_clicked(cls, well: str) -> None:
        """
        Append a clicked well to the session state.
        """
        clicked_wells = cls.get_wells_clicked()
        if well not in clicked_wells:
            clicked_wells.append(well)
            cls.set_wells_clicked(clicked_wells)

    @classmethod
    def remove_well_clicked(cls, well: str) -> None:
        """
        Remove a clicked well from the session state.
        """
        clicked_wells = cls.get_wells_clicked()
        if well in clicked_wells:
            clicked_wells.remove(well)
            cls.set_wells_clicked(clicked_wells)

    @classmethod
    def clear_wells_clicked(cls) -> None:
        """
        Clear the clicked wells from the session state.
        """
        cls.set_wells_clicked([])

    @classmethod
    def set_wells_clicked(cls, wells: List[str]) -> None:
        """
        Set the clicked wells in the session state.
        """
        st.session_state[cls.WELLS_CLICKED_KEY] = wells
        # If we are in multiple plates mode, we need to reset the output dir and the png metadata used for stats
        if cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
            cls.set_png_metadata({})
            cls.set_stats_folder(None)


    ######################################## SELECTED ROWS/COLS ########################################
    @classmethod
    def get_selected_rows(cls) -> List[chr]:
        """
        Get the selected rows from the session state.
        """
        return st.session_state.get(cls.SELECTED_ROWS_KEY, [])

    @classmethod
    def append_selected_row(cls, row: chr) -> None:
        """
        Append a selected row to the session state.
        """
        selected_rows = cls.get_selected_rows()
        if row not in selected_rows:
            selected_rows.append(row)
            st.session_state[cls.SELECTED_ROWS_KEY] = selected_rows

    @classmethod
    def remove_selected_row(cls, row: chr) -> None:
        """
        Remove a selected row from the session state.
        """
        selected_rows = cls.get_selected_rows()
        if row in selected_rows:
            selected_rows.remove(row)
            st.session_state[cls.SELECTED_ROWS_KEY] = selected_rows

    @classmethod
    def clear_selected_rows(cls) -> None:
        """
        Clear the selected rows from the session state.
        """
        st.session_state[cls.SELECTED_ROWS_KEY] = []

    @classmethod
    def get_selected_cols(cls) -> List[int]:
        """
        Get the selected columns from the session state.
        """
        return st.session_state.get(cls.SELECTED_COLS_KEY, [])

    @classmethod
    def append_selected_col(cls, col: int) -> None:
        """
        Append a selected column to the session state.
        """
        selected_cols = cls.get_selected_cols()
        if col not in selected_cols:
            selected_cols.append(col)
            st.session_state[cls.SELECTED_COLS_KEY] = selected_cols

    @classmethod
    def remove_selected_col(cls, col: int) -> None:
        """
        Remove a selected column from the session state.
        """
        selected_cols = cls.get_selected_cols()
        if col in selected_cols:
            selected_cols.remove(col)
            st.session_state[cls.SELECTED_COLS_KEY] = selected_cols

    @classmethod
    def clear_selected_cols(cls) -> None:
        """
        Clear the selected rows from the session state.
        """
        st.session_state[cls.SELECTED_COLS_KEY] = []

    ######################################## SELECTED REPLICATES WELLS ########################################

    @classmethod
    def get_replicates_saved(cls) -> List[str]:
        """
        Get the saved replicates from the session state.
        """
        return st.session_state.get(cls.REPLICATES_SAVED_KEY, None)

    @classmethod
    def set_replicates_saved(cls, replicates_saved: List[str]) -> None:
        """
        Set the saved replicates in the session state.
        """
        st.session_state[cls.REPLICATES_SAVED_KEY] = replicates_saved

    @classmethod
    def get_selected_replicates_wells(cls) -> List[str]:
        """
        Get the replicated wells show from the session state.
        """
        return st.session_state.get(cls.SELECTED_REPLICATES_WELLS_KEY, [])

    @classmethod
    def append_selected_replicates_wells(cls, well: str) -> None:
        """
        Append a replicated well to the session state.
        """
        selected_replicates_wells = cls.get_selected_replicates_wells()
        if well not in selected_replicates_wells:
            selected_replicates_wells.append(well)
            st.session_state[cls.SELECTED_REPLICATES_WELLS_KEY] = selected_replicates_wells

    @classmethod
    def remove_selected_replicates_wells(cls, well: str) -> None:
        """
        Remove a replicated well from the session state.
        """
        selected_replicates_wells = cls.get_selected_replicates_wells()
        if well in selected_replicates_wells:
            selected_replicates_wells.remove(well)
            st.session_state[cls.SELECTED_REPLICATES_WELLS_KEY] = selected_replicates_wells

    @classmethod
    def clear_selected_replicates_wells(cls) -> None:
        """
        Clear the replicated wells show from the session state.
        """
        st.session_state[cls.SELECTED_REPLICATES_WELLS_KEY] = []

    @classmethod
    def group_wells_by_options(cls, selected_well_or_replicate: str) -> Dict:
        """
        Group wells by the selected well or replicate.
        """
        if cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
            return cls._group_wells_by_options_multiple(selected_well_or_replicate)
        else:
            return cls._group_wells_by_options_single(selected_well_or_replicate)

    @classmethod
    def _group_wells_by_options_single(cls, selected_well_or_replicate: str) -> Dict:
        data = cls.get_data()
        dict_replicates = {}

        for key, biolector_experiment in data.items():
            for well, well_metadata in biolector_experiment.metadata.items():
                if selected_well_or_replicate in well_metadata and well in biolector_experiment.data.columns:
                    if well_metadata[selected_well_or_replicate] not in dict_replicates:
                        dict_replicates[well_metadata[selected_well_or_replicate]] = []
                    if well not in dict_replicates[
                            well_metadata[selected_well_or_replicate]]:
                        dict_replicates[well_metadata[selected_well_or_replicate]].append(well)

        return dict_replicates

    @classmethod
    def _group_wells_by_options_multiple(cls, selected_well_or_replicate: str) -> Dict:
        data = cls.get_data()
        dict_replicates = {}

        for key, biolector_experiment in data.items():
            for well, plate_metadata in biolector_experiment.metadata.items():
                for plate, metadata in plate_metadata.items():
                    if selected_well_or_replicate in metadata and f"{well}_{plate}" in biolector_experiment.data.columns:
                        if metadata[selected_well_or_replicate] not in dict_replicates:
                            dict_replicates[metadata[selected_well_or_replicate]] = {}
                        if plate not in dict_replicates[metadata[selected_well_or_replicate]]:
                            dict_replicates[metadata[selected_well_or_replicate]][plate] = []
                        if well not in dict_replicates[metadata[selected_well_or_replicate]][plate]:
                            dict_replicates[metadata[selected_well_or_replicate]][plate].append(well)

        return dict_replicates

    @classmethod
    def get_options_replicates(cls) -> List[str]:
        """
        Get the options replicates from the session state.
        """
        return st.session_state.get(cls.OPTIONS_REPLICATES, [])

    @classmethod
    def reset_options_replicates(cls, dict_replicates: Dict) -> None:
        """
        Reset the options replicates in the session state.
        """
        st.session_state[cls.OPTIONS_REPLICATES] = []
        # list of wells from A01 to B12
        cross_out_wells = {f"{row}{col:02d}" for row in "AB" for col in range(1, 13)}
        if cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
            cls.set_options_replicates_multiple(dict_replicates, cross_out_wells)
        else:
            cls.set_options_replicates_single(dict_replicates, cross_out_wells)

    @classmethod
    def set_options_replicates_single(cls, dict_replicates: Dict, cross_out_wells: List[str]) -> None:
        """
        Set the options replicates in the session state.
        """
        cross_out_wells = {f"{row}{col:02d}" for row in "AB" for col in range(1, 13)}
        for replicate, wells in dict_replicates.items():
            if cls.is_microfluidics() and any(well in cross_out_wells
                                              for well in wells):
                continue
            elif len(cls.get_wells_clicked()) > 0:
                if not any(well in dict_replicates[replicate] for well in cls.get_wells_clicked()):
                    continue
                else:
                    cls.add_option_replicate(replicate)
            else:
                cls.add_option_replicate(replicate)

    @classmethod
    def set_options_replicates_multiple(cls, dict_replicates: Dict, cross_out_wells: List[str]) -> None:
        """
        Set the options replicates in the session state.
        """
        st.session_state[cls.OPTIONS_REPLICATES] = []
        for replicate, replicate_plates in dict_replicates.items():
            for plate, wells in replicate_plates.items():
                if cls.is_microfluidics() and any(well in cross_out_wells
                                                  for well in wells):
                    continue
                elif len(cls.get_wells_clicked()) > 0:
                    if not any(well in dict_replicates[replicate][plate] for well in cls.get_wells_clicked()):
                        continue
                    else:
                        cls.add_option_replicate(replicate)
                else:
                    cls.add_option_replicate(replicate)

    @classmethod
    def add_option_replicate(cls, replicate: str) -> None:
        """
        Add an option replicate to the session state.
        """
        options_replicates = cls.get_options_replicates()
        if replicate not in options_replicates:
            options_replicates.append(replicate)
            st.session_state[cls.OPTIONS_REPLICATES] = options_replicates

    @classmethod
    def color_wells_replicates(cls, dict_replicates: Dict, selected_replicates: List[str]) -> None:
        """
        Color the wells replicates in the session state.
        """
        cls.set_replicates_saved(selected_replicates)
        cls.reset_session_state_wells()

        for replicate in selected_replicates:
            wells = dict_replicates[replicate]
            if cls.get_mode() == BiolectorStateMode.MULTIPLE_PLATES:
                for plate, wells in wells.items():
                    for well in wells:
                        if f"{well}_{plate}" not in cls.get_wells_to_show():
                            cls.append_wells_to_show(f"{well}_{plate}")
                        if well not in cls.get_replicated_wells_show():
                            cls.append_replicated_wells_show(well)
            else:
                for well in wells:
                    cls.append_replicated_wells_show(well)
                    cls.append_wells_to_show(well)

    @classmethod
    def reset_session_state_wells(cls) -> None:
        st.session_state[cls.REPLICATED_WELLS_SHOW_KEY] = []
        st.session_state[cls.WELLS_TO_SHOW_KEY] = []

    @classmethod
    def get_replicated_wells_show(cls) -> List:
        return st.session_state.get(cls.REPLICATED_WELLS_SHOW_KEY, [])

    @classmethod
    def append_replicated_wells_show(cls, well: str) -> None:
        wells = cls.get_replicated_wells_show()
        if well not in wells:
            wells.append(well)
            st.session_state[cls.REPLICATED_WELLS_SHOW_KEY] = wells

    @classmethod
    def get_wells_to_show(cls) -> List:
        return st.session_state.get(cls.WELLS_TO_SHOW_KEY, [])

    @classmethod
    def append_wells_to_show(cls, wells: str) -> None:
        wells_to_show = cls.get_wells_to_show()
        if wells not in wells_to_show:
            wells_to_show.append(wells)
            st.session_state[cls.WELLS_TO_SHOW_KEY] = wells_to_show

    @classmethod
    def get_table_by_filter(
            cls, selected_well_or_replicate: str, filter: str, selected_replicates: List[str]) -> DataFrame:
        """
        Get the table by filter.
        """
        data = cls.get_data()
        experiments: List[BiolectorExperiment] = []
        for key, biolector_experiment in data.items():
            if biolector_experiment.filter == filter:
                experiments.append(biolector_experiment)

        if len(experiments) == 0:
            raise ValueError(f"Filter '{filter}' not found in data.")

        df = experiments[0].data
        wells_selected = None
        if len(BiolectorState.get_wells_clicked()) > 0:
            wells_selected = BiolectorState.get_wells_clicked()

        if selected_replicates:
            wells_selected = BiolectorState.get_replicated_wells_show()
            # Filter df with the wells to keep, keep the columns that start with the wells
            columns = [col for col in df.columns if col.split(
                '_')[0] in wells_selected if col not in ['time', 'Temps_en_h']]
            df = df[["time", "Temps_en_h"] + columns]

        if not wells_selected:
            return df

        else:
            if cls.get_mode() != BiolectorStateMode.MULTIPLE_PLATES:
                return df[["time", "Temps_en_h"] + wells_selected]
            else:
                columns = [col for col in df.columns if col.split(
                    '_')[0] in wells_selected if col not in ['time', 'Temps_en_h']]
                return df[["time", "Temps_en_h"] + columns]

    @classmethod
    def get_stats_folder(cls) -> str:
        """
        Get the stats folder from the session state.
        """
        return st.session_state.get(cls.STATS_FOLDER_KEY, None)

    @classmethod
    def set_stats_folder(cls, stats_folder: str) -> None:
        """
        Set the stats folder in the session state.
        """
        st.session_state[cls.STATS_FOLDER_KEY] = stats_folder

    @classmethod
    def get_png_metadata(cls) -> Dict:
        """
        Get the PNG metadata from the session state.
        """
        return st.session_state.get(cls.PNG_METADATA_KEY, {})

    @classmethod
    def set_png_metadata(cls, png_metadata: Dict) -> None:
        """
        Set the PNG metadata in the session state.
        """
        st.session_state[cls.PNG_METADATA_KEY] = png_metadata

    @classmethod
    def get_plot_mode(cls) -> str:
        """
        Get the plot mode from the session state.
        """
        return st.session_state.get(cls.PLOT_MODE_KEY, None)

    @classmethod
    def set_plot_mode(cls, plot_mode: str) -> None:
        """
        Set the plot mode in the session state.
        """
        st.session_state[cls.PLOT_MODE_KEY] = plot_mode

    @classmethod
    def get_plot_time(cls) -> str:
        """
        Get the plot time from the session state.
        """
        return st.session_state.get(cls.PLOT_TIME_KEY, None)

    @classmethod
    def set_plot_time(cls, plot_time: str) -> None:
        """
        Set the plot time in the session state.
        """
        st.session_state[cls.PLOT_TIME_KEY] = plot_time

    @classmethod
    def get_error_band(cls) -> bool:
        """
        Get the error band from the session state.
        """
        return st.session_state.get(cls.ERROR_BAND_KEY, False)

    @classmethod
    def set_error_band(cls, error_band: bool) -> None:
        """
        Set the error band in the session state.
        """
        st.session_state[cls.ERROR_BAND_KEY] = error_band

    @classmethod
    def get_display_success_message_resource_table(cls) ->bool:
        """
        Get the success message resource table from the session state.
        """
        return st.session_state.get(cls.SUCCESS_MESSAGE_RESOURCE_TABLE_KEY, False)

    @classmethod
    def set_display_success_message_resource_table(cls, display: bool) -> None:
        """
        Set the success message resource table in the session state.
        """
        st.session_state[cls.SUCCESS_MESSAGE_RESOURCE_TABLE_KEY] = display