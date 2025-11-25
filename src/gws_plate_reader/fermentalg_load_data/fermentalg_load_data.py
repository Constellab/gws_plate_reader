import os
import re

import pandas as pd
import numpy as np
import plotly.graph_objects as go

from gws_core import (File, InputSpec, OutputSpec, InputSpecs, OutputSpecs, Table, Folder, Tag,
                      TypingStyle, ResourceSet, Task, task_decorator, TableImporter, ZipCompress,
                      PlotlyResource)

from typing import Dict, Any, Set, Tuple


def create_venn_diagram_3_sets(sample_sets: Dict[str, Set[Tuple[str, str]]]) -> go.Figure:
    """
    Create a Venn diagram with 3 overlapping circles representing data types
    (info, raw_data, follow_up) showing all intersections.

    Args:
        sample_sets: Dict with sets of (batch, sample) tuples for each data type
            Keys: 'info', 'raw_data', 'follow_up'
            Values: Set of (batch, sample) tuples

    Returns:
        Plotly Figure with the Venn diagram showing all intersections
    """

    # Extract sets
    A = sample_sets.get('info', set())  # Info
    B = sample_sets.get('raw_data', set())  # Raw Data
    C = sample_sets.get('follow_up', set())  # Follow-up

    # Calculate all regions
    only_A = len(A - B - C)  # Only Info
    only_B = len(B - A - C)  # Only Raw Data
    only_C = len(C - A - B)  # Only Follow-up
    A_and_B = len((A & B) - C)  # Info ∩ Raw Data (excluding Follow-up)
    A_and_C = len((A & C) - B)  # Info ∩ Follow-up (excluding Raw Data)
    B_and_C = len((B & C) - A)  # Raw Data ∩ Follow-up (excluding Info)
    A_and_B_and_C = len(A & B & C)  # All three (complete samples)

    # Create figure
    fig = go.Figure()

    # Circle parameters
    radius = 0.28
    Ax, Ay = 0.35, 0.5   # Info (left)
    Bx, By = 0.65, 0.5   # Raw Data (right)
    Cx, Cy = 0.5, 0.72   # Follow-up (top)

    # Create circles using parametric equations
    theta = np.linspace(0, 2 * np.pi, 100)

    # Circle A - Info (Blue)
    x_A = radius * np.cos(theta) + Ax
    y_A = radius * np.sin(theta) + Ay
    fig.add_trace(go.Scatter(
        x=x_A, y=y_A,
        fill='toself',
        fillcolor='rgba(33, 150, 243, 0.3)',
        line=dict(color='rgba(33, 150, 243, 0.8)', width=3),
        name='Info',
        mode='lines',
        hoverinfo='skip',
        showlegend=False
    ))

    # Circle B - Raw Data (Green)
    x_B = radius * np.cos(theta) + Bx
    y_B = radius * np.sin(theta) + By
    fig.add_trace(go.Scatter(
        x=x_B, y=y_B,
        fill='toself',
        fillcolor='rgba(76, 175, 80, 0.3)',
        line=dict(color='rgba(76, 175, 80, 0.8)', width=3),
        name='Raw Data',
        mode='lines',
        hoverinfo='skip',
        showlegend=False
    ))

    # Circle C - Follow-up (Purple)
    x_C = radius * np.cos(theta) + Cx
    y_C = radius * np.sin(theta) + Cy
    fig.add_trace(go.Scatter(
        x=x_C, y=y_C,
        fill='toself',
        fillcolor='rgba(156, 39, 176, 0.3)',
        line=dict(color='rgba(156, 39, 176, 0.8)', width=3),
        name='Follow-up',
        mode='lines',
        hoverinfo='skip',
        showlegend=False
    ))

    # Add titles near the top of each circle
    fig.add_annotation(x=Ax, y=Ay + radius + 0.05, text="<b>Info</b>",
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Bx, y=By + radius + 0.05, text="<b>Raw Data</b>",
                       showarrow=False, font=dict(size=14))
    fig.add_annotation(x=Cx, y=Cy + radius + 0.05, text="<b>Follow-up</b>",
                       showarrow=False, font=dict(size=14))

    # Add region counts (manually positioned for clarity)
    # Only A (Info only)
    fig.add_annotation(x=Ax - 0.13, y=Ay, text=str(only_A),
                       showarrow=False, font=dict(size=14))

    # Only B (Raw Data only)
    fig.add_annotation(x=Bx + 0.13, y=By, text=str(only_B),
                       showarrow=False, font=dict(size=14))

    # Only C (Follow-up only)
    fig.add_annotation(x=Cx, y=Cy + 0.18, text=str(only_C),
                       showarrow=False, font=dict(size=14))

    # A ∩ B (excluding C) - Info & Raw Data
    fig.add_annotation(x=(Ax + Bx) / 2, y=Ay - 0.08, text=str(A_and_B),
                       showarrow=False, font=dict(size=14))

    # A ∩ C (excluding B) - Info & Follow-up
    fig.add_annotation(x=Ax + 0.07, y=Ay + 0.16, text=str(A_and_C),
                       showarrow=False, font=dict(size=14))

    # B ∩ C (excluding A) - Raw Data & Follow-up
    fig.add_annotation(x=Bx - 0.07, y=By + 0.16, text=str(B_and_C),
                       showarrow=False, font=dict(size=14))

    # A ∩ B ∩ C (center) - All three (complete)
    fig.add_annotation(
        x=Cx, y=Ay + 0.1,
        text=f"<b>{A_and_B_and_C}</b>",
        showarrow=False,
        font=dict(size=16, color='darkgreen'),
        bgcolor='rgba(255, 255, 255, 0.9)',
        borderpad=4,
        bordercolor='darkgreen',
        borderwidth=2
    )

    # Update layout
    fig.update_layout(
        title="Data Availability - Venn Diagram (Info, Raw Data, Follow-up)", showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(
            showticklabels=False, showgrid=False, zeroline=False, range=[0.2, 1.05],
            scaleanchor="x", scaleratio=1),
        height=600, width=600, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',)

    return fig


@task_decorator("FermentalgLoadData", human_name="Load Fermentalg data QC0",
                short_description="Load and process Fermentalg QC0 fermentation data from multiple sources",
                style=TypingStyle.community_icon(icon_technical_name="file-upload", background_color="#2492FE"))
class FermentalgLoadData(Task):
    """
    Load and process Fermentalg QC0 fermentation data from multiple CSV files and follow-up data.

    ## Overview
    This task integrates data from four different sources to create a comprehensive dataset
    for fermentation analysis. It handles data merging, validation, missing data detection,
    and generates a visual summary of data availability.

    ## Input Files Required

    ### 1. Info CSV (`info_csv`)
    Contains experiment and fermenter information with columns:
    - `ESSAI`: Experiment/trial identifier (e.g., "EPA-WP3-25-001")
    - `FERMENTEUR`: Fermenter identifier (e.g., "23A", "23B")
    - `MILIEU`: Culture medium used
    - Additional metadata columns describing experimental conditions

    ### 2. Raw Data CSV (`raw_data_csv`)
    Contains raw measurement data with columns:
    - `ESSAI`: Experiment identifier (must match Info CSV)
    - `FERMENTEUR`: Fermenter identifier (must match Info CSV)
    - `Temps de culture (h)`: Culture time in hours
    - Multiple measurement columns (e.g., biomass, pH, temperature)

    ### 3. Medium CSV (`medium_csv`)
    Contains culture medium composition with columns:
    - `MILIEU`: Medium identifier (must match Info CSV)
    - Composition columns describing medium components and concentrations

    ### 4. Follow-up ZIP (`follow_up_zip`)
    ZIP archive containing CSV files with temporal tracking data:
    - Filenames must follow pattern: `<ESSAI> <FERMENTEUR>.csv`
    - Example: "EPA-WP3-25-001 23A.csv"
    - Contains time-series data with temporal measurements
    - Column `Temps (h)` will be renamed to `Temps de culture (h)` for consistency

    ## Processing Steps

    1. **File Loading**: Imports all CSV files and unzips follow-up data
    2. **Data Indexing**: Creates lookup tables for each (ESSAI, FERMENTEUR) pair
    3. **Data Merging**:
       - Merges Raw Data and Follow-up data on time column
       - Normalizes decimal formats (comma → dot)
       - Filters negative time values
       - Performs outer join to preserve all data points
    4. **Metadata Enrichment**: Adds batch, sample, and medium information as tags
    5. **Missing Data Detection**: Identifies which data types (info/raw_data/medium/follow_up)
       are missing for each sample
    6. **Column Tagging**: Automatically tags columns as:
       - `is_index_column`: Time columns
       - `is_data_column`: Measurement columns
       - Metadata columns (ESSAI, FERMENTEUR, MILIEU)

    ## Outputs

    ### 1. Resource Set (`resource_set`)
    A ResourceSet containing one Table per (ESSAI, FERMENTEUR) combination:
    - **Table Name**: `<ESSAI>_<FERMENTEUR>`
    - **Tags**:
      - `batch`: Experiment identifier (ESSAI)
      - `sample`: Fermenter identifier (FERMENTEUR)
      - `medium`: Culture medium name
      - `missing_value`: Comma-separated list of missing data types (if any)
        - Possible values: "info", "raw_data", "medium", "follow_up", "follow_up_empty"
    - **Column Tags**:
      - `is_index_column='true'`: Time columns for plotting
      - `is_data_column='true'`: Measurement columns
      - `unit`: Unit of measurement (when available)

    ### 2. Venn Diagram (`venn_diagram`) - Optional
    A PlotlyResource containing an interactive Venn diagram showing:
    - **4 Overlapping Circles**: One per data type (Info, Raw Data, Medium, Follow-up)
    - **Circle Labels**: Show count of samples with that data type
    - **Center Label**: Shows count of complete samples (all 4 data types present)
    - **Color Coding**:
      - Blue: Info data
      - Green: Raw Data
      - Orange: Medium data
      - Purple: Follow-up data

    ### 3. Medium Table (`medium_table`) - Optional
    The medium composition CSV file converted to a Table resource with proper data types:
    - **First column** (MILIEU): Kept as string (medium name/identifier)
    - **Other columns**: Converted to float (handles both comma and dot as decimal separator)
    - **Missing values**: Empty cells or non-numeric text converted to NaN

    ### 4. Feature Matrix X (`X`)
    A Table containing one row per experiment (ESSAI, FERMENTEUR) with features for machine learning:
    - **Identifier Column**:
      - `experiment_id`: Unique experiment identifier formatted as `ESSAI_FERMENTEUR_MILIEU`
    - **Medium Composition Columns** (prefixed with `medium_`):
      - All components from the medium CSV (e.g., `medium_glucose`, `medium_nitrogen`)
      - Values are numeric concentrations
      - Columns with only NaN or 0 values are automatically removed
    - **Initial Parameter Columns** (prefixed with `alpha_`):
      - First value (t0) of each column from follow-up files
      - Example: `alpha_temp`, `alpha_pH`, `alpha_DO`
      - Represents initial conditions of the experiment
      - Columns with only NaN or 0 values are automatically removed
    - **Constant Columns** (prefixed with `constant_`):
      - Columns from raw_data that have the same value for all timepoints
      - Example: `constant_setpoint_temp`, `constant_inoculum`
      - Represents experimental parameters that don't change over time
      - Columns with only NaN or 0 values are automatically removed

    ### 5. Target Matrix y (`y`)
    A Table containing one row per experiment with target values for machine learning:
    - **Identifier Column**:
      - `experiment_id`: Unique experiment identifier formatted as `ESSAI_FERMENTEUR_MILIEU`
    - **Final Value Columns** (prefixed with `final_`):
      - Last measured value of each non-constant column from raw_data
      - Example: `final_biomass`, `final_pH`, `final_substrate`
      - Represents the experimental outcomes/results

    ## Data Quality

    ### Missing Data Handling
    The task detects and reports missing data through tags:
    - Samples with missing Info will have `missing_value` tag including "info"
    - Samples with missing Raw Data will have tag including "raw_data"
    - Samples with missing Medium will have tag including "medium"
    - Samples with missing Follow-up will have tag including "follow_up"
    - Samples with empty Follow-up files will have tag including "follow_up_empty"

    ### Data Validation
    - Checks for matching (ESSAI, FERMENTEUR) pairs across all data sources
    - Normalizes decimal separators for consistent numeric parsing
    - Filters out negative time values from follow-up data
    - Preserves all original columns and metadata

    ## Use Cases

    1. **Quality Control**: Use Venn diagram to quickly assess data completeness
    2. **Exploratory Analysis**: Browse merged data with all temporal measurements
    3. **Selective Processing**: Use tags to filter complete vs incomplete samples
    4. **Dashboard Display**: Visualize data availability and sample information
    5. **Downstream Analysis**: Provides clean, tagged data for filtering and interpolation

    ## Example Workflow

    ```
    [Info CSV] ──┐
    [Raw Data] ──┼──> FermentalgLoadData ──┬──> [Resource Set] ──> Filter/Analysis
    [Medium]   ──┤                          ├──> [Venn Diagram] ──> Dashboard
    [Follow-up]──┘                          └──> [Medium Table] ──> PCA/UMAP
    ```

    ## Notes

    - All CSV files should use UTF-8, Latin-1, or CP1252 encoding
    - Accepted separators: comma (,) or semicolon (;)
    - Column names are normalized to uppercase for matching
    - Follow-up files starting with "._" (macOS metadata) are ignored
    - Time columns are automatically detected and tagged for indexing
    - Output tables can be directly used with Filter and Interpolation tasks
    """
    input_specs: InputSpecs = InputSpecs(
        {
            'info_csv': InputSpec(File, human_name="Info CSV file", optional=False),
            'raw_data_csv': InputSpec(File, human_name="Raw data CSV file", optional=False),
            'medium_csv': InputSpec(File, human_name="Medium CSV file", optional=False),
            'follow_up_zip': InputSpec(File, human_name="Follow-up ZIP file", optional=False),
        }
    )

    output_specs: OutputSpecs = OutputSpecs(
        {'resource_set': OutputSpec(ResourceSet, human_name="Resource set containing all the tables"),
         'venn_diagram': OutputSpec(
             PlotlyResource, human_name="Venn diagram of data availability", optional=True),
         'medium_table':
         OutputSpec(
             Table, human_name="Medium composition table",
             short_description="Medium CSV file with numeric columns properly converted to float", optional=True)})

    def run(self, params, inputs):

        info_file: File = inputs['info_csv']
        raw_data_file: File = inputs['raw_data_csv']
        medium_file: File = inputs['medium_csv']
        follow_up_file: File = inputs['follow_up_zip']

        info_table: Table = TableImporter.call(info_file)
        raw_data_table: Table = TableImporter.call(raw_data_file)
        medium_table: Table = TableImporter.call(medium_file)

        info_table.name = "Info table"
        raw_data_table.name = "Raw data table"
        medium_table.name = "Medium table"

        follow_up_folder_path = os.path.splitext(follow_up_file.path)[0]

        ZipCompress.decompress(follow_up_file.path, follow_up_folder_path)

        follow_up_folder = Folder(follow_up_folder_path)

        follow_up_folder_name = ''
        for folder in follow_up_folder.list_dir():
            if not folder.startswith('_'):
                follow_up_folder_name = folder
                break

        follow_up_dict: Dict[str, Table] = {}  # key format : "Essai Fermentor"

        for file_path in Folder(f"{follow_up_folder_path}/{follow_up_folder_name}").list_dir():
            file = File(f"{follow_up_folder_path}/{follow_up_folder_name}/{file_path}")
            table = TableImporter.call(file)
            table.name = os.path.splitext(file_path)[0]
            follow_up_dict[table.name] = table

        print(f"Fichiers de suivi trouvés: {list(follow_up_dict.keys())}")

        full_info_dict: Dict[str, Any] = {}

        info_df: pd.DataFrame = info_table.get_data()
        raw_data_df: pd.DataFrame = raw_data_table.get_data()
        medium_df: pd.DataFrame = medium_table.get_data()

        # Récupérer tous les couples distincts des deux tables
        couples_info = info_df[['ESSAI', 'FERMENTEUR']].drop_duplicates()
        couples_raw_data = raw_data_df[['ESSAI', 'FERMENTEUR']].drop_duplicates()

        # Extraire aussi les couples depuis les fichiers de suivi
        # Format des clés : "ESSAI FERMENTEUR"
        couples_follow_up_data = []
        for follow_up_key in follow_up_dict.keys():
            parts = follow_up_key.split(' ', 1)  # Split sur le premier espace uniquement
            if len(parts) == 2:
                couples_follow_up_data.append({'ESSAI': parts[0], 'FERMENTEUR': parts[1]})

        couples_follow_up = pd.DataFrame(couples_follow_up_data) if couples_follow_up_data else pd.DataFrame(
            columns=['ESSAI', 'FERMENTEUR'])

        # Combiner tous les couples distincts (union)
        tous_couples = pd.concat([couples_info, couples_raw_data, couples_follow_up]
                                 ).drop_duplicates().reset_index(drop=True)

        for _, row in tous_couples.iterrows():
            essai = row['ESSAI']
            fermentor = row['FERMENTEUR']
            if essai not in full_info_dict:
                full_info_dict[essai] = {}
            if fermentor not in full_info_dict[essai]:
                full_info_dict[essai][fermentor] = {}

            if 'medium' in full_info_dict[essai][fermentor]:
                continue

            # Récupérer le medium depuis info_df si disponible
            info_filtered = info_df[(info_df['ESSAI'] == essai) & (info_df['FERMENTEUR'] == fermentor)]
            if not info_filtered.empty:
                medium = info_filtered['MILIEU'].values[0]
                full_info_dict[essai][fermentor]['medium'] = medium
                full_info_dict[essai][fermentor]['info'] = info_filtered
            else:
                full_info_dict[essai][fermentor]['medium'] = None
                full_info_dict[essai][fermentor]['info'] = pd.DataFrame()

            # Récupérer les raw_data si disponibles
            raw_data_filtered = raw_data_df[(raw_data_df['ESSAI'] == essai) & (raw_data_df['FERMENTEUR'] == fermentor)]
            full_info_dict[essai][fermentor]['raw_data'] = raw_data_filtered

            # Récupérer les medium_data si le medium existe
            if full_info_dict[essai][fermentor]['medium'] is not None and 'MILIEU' in medium_df.columns:
                medium_data_filtered = medium_df[medium_df['MILIEU'] == full_info_dict[essai][fermentor]['medium']]
                medium_data_filtered = medium_data_filtered.drop(columns=['MILIEU'])
                full_info_dict[essai][fermentor]['medium_data'] = medium_data_filtered
            else:
                full_info_dict[essai][fermentor]['medium_data'] = pd.DataFrame()

            # Vérifier si un fichier de suivi existe pour ce couple
            follow_up_key = f"{essai} {fermentor}"
            full_info_dict[essai][fermentor]['has_follow_up'] = follow_up_key in follow_up_dict
            if follow_up_key in follow_up_dict:
                full_info_dict[essai][fermentor]['follow_up_table'] = follow_up_dict[follow_up_key]
                print(f"Fichier de suivi trouvé pour {follow_up_key}")
            else:
                full_info_dict[essai][fermentor]['follow_up_table'] = Table(pd.DataFrame())
                print(f"Aucun fichier de suivi pour {follow_up_key}")

        res: ResourceSet = ResourceSet()

        for essai, fermentors in full_info_dict.items():
            for fermentor, data in fermentors.items():
                try:
                    row_data_df: pd.DataFrame = data['raw_data']
                    # Utiliser les informations stockées dans full_info_dict
                    follow_up_df: pd.DataFrame = data['follow_up_table'].get_data()

                    # Merger raw_data_df et follow_up_df sur la colonne 'Temps de culture (h)'
                    if not row_data_df.empty and not follow_up_df.empty:
                        # Renommer la colonne de temps dans follow_up_df pour correspondre à raw_data_df
                        if 'Temps (h)' in follow_up_df.columns:
                            follow_up_df = follow_up_df.rename(columns={'Temps (h)': 'Temps de culture (h)'})

                        # Normaliser les formats numériques des colonnes de temps
                        def normalize_decimal_format(df, column_name):
                            """Convertit les virgules en points et assure le type float"""
                            if column_name in df.columns:
                                # Convertir en string puis remplacer virgules par points
                                df[column_name] = df[column_name].astype(str).str.replace(',', '.', regex=False)
                                # Convertir en float
                                df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
                            return df

                        # Normaliser les deux DataFrames
                        row_data_df = normalize_decimal_format(row_data_df.copy(), 'Temps de culture (h)')
                        follow_up_df = normalize_decimal_format(follow_up_df.copy(), 'Temps de culture (h)')

                        # Filtrer les lignes avec temps négatif dans follow_up_df
                        if 'Temps de culture (h)' in follow_up_df.columns:
                            follow_up_df = follow_up_df[follow_up_df['Temps de culture (h)'] >= 0]

                        # Assurer que les colonnes de temps ont le même type (float) pour éviter le warning
                        if 'Temps de culture (h)' in row_data_df.columns:
                            row_data_df['Temps de culture (h)'] = row_data_df['Temps de culture (h)'].astype(float)
                        if 'Temps de culture (h)' in follow_up_df.columns:
                            follow_up_df['Temps de culture (h)'] = follow_up_df['Temps de culture (h)'].astype(float)

                        # Merge sur la colonne 'Temps de culture (h)'
                        full_df = pd.merge(
                            row_data_df,
                            follow_up_df,
                            on='Temps de culture (h)',
                            how='outer'  # outer join pour garder toutes les données
                        )
                    elif not row_data_df.empty:
                        full_df = row_data_df.copy()
                    elif not follow_up_df.empty:
                        # Renommer la colonne de temps si nécessaire
                        if 'Temps (h)' in follow_up_df.columns:
                            follow_up_df = follow_up_df.rename(columns={'Temps (h)': 'Temps de culture (h)'})

                        # Normaliser le format et filtrer les temps négatifs
                        def normalize_decimal_format(df, column_name):
                            """Convertit les virgules en points et assure le type float"""
                            if column_name in df.columns:
                                # Convertir en string puis remplacer virgules par points
                                df[column_name] = df[column_name].astype(str).str.replace(',', '.', regex=False)
                                # Convertir en float
                                df[column_name] = pd.to_numeric(df[column_name], errors='coerce')
                            return df

                        follow_up_df = normalize_decimal_format(follow_up_df.copy(), 'Temps de culture (h)')

                        # Filtrer les lignes avec temps négatif
                        if 'Temps de culture (h)' in follow_up_df.columns:
                            follow_up_df = follow_up_df[follow_up_df['Temps de culture (h)'] >= 0]

                        full_df = follow_up_df.copy()
                    else:
                        # Aucune donnée temporelle (ni raw_data ni follow_up)
                        # Créer un DataFrame avec juste les infos si elles existent
                        if not data['info'].empty:
                            full_df = data['info'].copy()
                        else:
                            full_df = pd.DataFrame()

                    # Créer une Table pour chaque couple (essai, fermentor)
                    # même si full_df est vide, pour avoir les tags batch/sample dans le ResourceSet
                    if not full_df.empty or not data['info'].empty:
                        # Supprimer les colonnes entièrement vides (toutes NaN/None/null/chaînes vides)
                        # Conserver seulement les colonnes qui ont au moins une valeur non-null et non-vide
                        columns_to_keep = []
                        removed_columns = []

                        for col in full_df.columns:
                            # Vérifier si la colonne a au moins une valeur valide
                            col_data = full_df[col]

                            # Conditions pour considérer une colonne comme vide :
                            # 1. Toutes les valeurs sont NaN/None
                            is_all_nan = col_data.isna().all()

                            # Pour les colonnes de type object/string, vérifier aussi les chaînes vides
                            is_all_empty = False
                            if not is_all_nan and col_data.dtype == 'object':
                                # Ne convertir que les valeurs non-NaN en string
                                non_null_values = col_data.dropna()
                                if len(non_null_values) > 0:
                                    # Vérifier si toutes les valeurs non-null sont des chaînes vides
                                    is_all_empty = non_null_values.astype(str).str.strip().eq('').all()
                                else:
                                    is_all_empty = True

                            # La colonne est vide si elle est soit toute NaN, soit toute vide (pour strings)
                            if is_all_nan or is_all_empty:
                                removed_columns.append(col)
                            else:
                                columns_to_keep.append(col)

                        # Si des colonnes ont été supprimées, les enlever du DataFrame
                        if removed_columns:
                            full_df = full_df[columns_to_keep]
                            print(f"Colonnes vides supprimées pour {essai}_{fermentor}: {removed_columns}")

                        # Vérifier si le DataFrame n'est pas complètement vide après suppression des colonnes
                        if full_df.empty or len(columns_to_keep) == 0:
                            print(f"Aucune donnée valide pour {essai}_{fermentor}, passage au suivant")
                            continue

                        # Normaliser toutes les valeurs numériques (remplacer virgules par points)
                        def normalize_all_numeric_columns(df):
                            """Normalise toutes les colonnes qui pourraient contenir des valeurs numériques"""
                            df_normalized = df.copy()

                            for col in df_normalized.columns:
                                # Ignorer les colonnes clairement non-numériques
                                if col in ['ESSAI', 'FERMENTEUR', 'MILIEU']:
                                    continue

                                # Pour toutes les autres colonnes, essayer de normaliser
                                try:
                                    # Convertir en string pour pouvoir remplacer les virgules
                                    col_str = df_normalized[col].astype(str)

                                    # Remplacer les virgules par des points (format français -> anglais)
                                    col_str = col_str.str.replace(',', '.', regex=False)

                                    # Essayer de convertir en numérique
                                    # Si ça marche, c'est une colonne numérique
                                    numeric_values = pd.to_numeric(col_str, errors='coerce')

                                    # Vérifier si la colonne contient des valeurs numériques valides
                                    # (au moins une valeur non-NaN après conversion)
                                    if not numeric_values.isna().all():
                                        # Si oui, remplacer la colonne par les valeurs normalisées
                                        df_normalized[col] = numeric_values
                                        print(
                                            f"Colonne '{col}' normalisée (virgules -> points) pour {essai}_{fermentor}")
                                    # Sinon, garder les valeurs originales (probablement du texte)

                                except Exception as e:
                                    # En cas d'erreur, garder les valeurs originales
                                    print(
                                        f"Impossible de normaliser la colonne '{col}' pour {essai}_{fermentor}: {str(e)}")
                                    continue

                            return df_normalized

                        # Appliquer la normalisation
                        full_df = normalize_all_numeric_columns(full_df)

                        # Ajouter les colonnes ESSAI et FERMENTEUR au début du DataFrame seulement si elles n'existent pas déjà
                        if 'ESSAI' not in full_df.columns:
                            full_df.insert(0, 'ESSAI', essai)
                        else:
                            # Si la colonne existe déjà, s'assurer qu'elle contient la bonne valeur
                            full_df['ESSAI'] = essai

                        if 'FERMENTEUR' not in full_df.columns:
                            # Trouver la bonne position d'insertion (après ESSAI si elle existe)
                            if 'ESSAI' in full_df.columns:
                                essai_index = full_df.columns.get_loc('ESSAI')
                                insert_index = essai_index + 1
                            else:
                                insert_index = 0
                            full_df.insert(insert_index, 'FERMENTEUR', fermentor)
                        else:
                            # Si la colonne existe déjà, s'assurer qu'elle contient la bonne valeur
                            full_df['FERMENTEUR'] = fermentor

                        merged_table: Table = Table(full_df)
                        merged_table.name = f"{essai}_{fermentor}"

                        tags = [
                            Tag('batch', essai),
                            Tag('sample', fermentor)
                        ]

                        # Vérifier les données manquantes et ajouter les tags correspondants
                        missing_values = []

                        # Vérifier si les informations (info) manquent
                        if data['info'].empty:
                            missing_values.append('info')

                        # Vérifier si les données brutes (raw_data) manquent
                        if data['raw_data'].empty:
                            missing_values.append('raw_data')

                        # Vérifier si les données de medium manquent
                        if data['medium'] is None or data['medium_data'].empty:
                            missing_values.append('medium')

                        # Vérifier si les fichiers de suivi manquent
                        follow_up_key = f"{essai} {fermentor}"
                        has_follow_up_file = follow_up_key in follow_up_dict

                        # Debug: log follow-up detection
                        self.log_info_message(f"Checking follow-up for {follow_up_key}: has_file={has_follow_up_file}")

                        # Vérifier l'état du fichier de suivi
                        if not has_follow_up_file:
                            # Pas de fichier de suivi du tout
                            missing_values.append('follow_up')
                            self.log_info_message(f"  → No follow-up file, added 'follow_up' to missing_values")
                        else:
                            # Le fichier existe, vérifier s'il est vide
                            follow_up_data = follow_up_dict[follow_up_key].get_data()
                            if follow_up_data.empty:
                                missing_values.append('follow_up_empty')
                                self.log_info_message(
                                    f"  → Follow-up file is empty, added 'follow_up_empty' to missing_values")
                            else:
                                self.log_info_message(f"  → Follow-up file exists and is not empty")

                        # Ajouter le tag missing_value si des données manquent
                        if missing_values:
                            tags.append(Tag('missing_value', ', '.join(missing_values)))

                        if data['medium'] is not None:
                            medium_data: Dict = data['medium_data'].iloc[0].to_dict(
                            ) if not data['medium_data'].empty else {}
                            tags.append(Tag('medium', data['medium'], additional_info={'composed': medium_data}))

                        # Ajouter les tags à la table
                        for tag in tags:
                            merged_table.tags.add_tag(tag)

                        # Ajouter les tags spéciaux pour les colonnes ESSAI et FERMENTEUR
                        merged_table.add_column_tag_by_name('ESSAI', 'column_name', 'Essai')
                        merged_table.add_column_tag_by_name('FERMENTEUR', 'column_name', 'Fermenteur')

                        for col in merged_table.column_names:
                            # Ignorer les colonnes ESSAI et FERMENTEUR car elles sont déjà traitées
                            if col in ['ESSAI', 'FERMENTEUR']:
                                continue

                            # Pattern pour capturer le nom et l'unité entre parenthèses
                            match = re.match(r'^(.+?)\s*\(([^)]+)\)\s*$', col)

                            if match:
                                # Colonne avec unité
                                column_name = match.group(1).strip()
                                unit = match.group(2).strip()
                            else:
                                # Colonne sans unité
                                column_name = col.strip()
                                unit = None

                            # Créer les variables pour cette colonne
                            merged_table.add_column_tag_by_name(col, 'column_name', column_name)
                            if unit is not None:
                                merged_table.add_column_tag_by_name(col, 'unit', unit)

                            # Ajouter les tags is_index_column et is_data_column
                            # Identifier les colonnes métadonnées (batch, sample, medium)
                            metadata_columns = ['ESSAI', 'FERMENTEUR']
                            medium_related_columns = ['MILIEU', 'MEDIUM']  # Colonnes liées au milieu

                            # Identifier les colonnes de temps (index)
                            time_columns = ['Temps de culture (h)', 'Temps (h)', 'Temps']
                            is_time_column = (col in time_columns or
                                              column_name.lower() in ['temps', 'time'] or
                                              'temps' in column_name.lower())

                            # Identifier si c'est une colonne de milieu
                            is_medium_column = (col in medium_related_columns or
                                                column_name.upper() in medium_related_columns or
                                                'milieu' in column_name.lower() or
                                                'medium' in column_name.lower())

                            if is_time_column:
                                # Tag pour colonne d'index (Temps)
                                merged_table.add_column_tag_by_name(col, 'is_index_column', 'true')
                            elif col not in metadata_columns and not is_medium_column:
                                # Tag pour colonne de données (ni metadata, ni temps, ni milieu)
                                merged_table.add_column_tag_by_name(col, 'is_data_column', 'true')

                        res.add_resource(merged_table)
                except Exception as e:
                    self.log_error_message(f"Error processing {essai}_{fermentor}: {str(e)}")
                    continue

        # Calculate statistics for Venn diagram - Track (batch, sample) pairs for each data type
        sample_sets = {
            'info': set(),
            'raw_data': set(),
            'follow_up': set()
        }

        # Analyze all resources to build sets of samples with each data type
        for resource_name, resource in res.get_resources().items():
            if isinstance(resource, Table):
                # Extract batch and sample from tags
                batch = ""
                sample = ""
                missing_value = ""

                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == 'batch':
                            batch = tag.value
                        elif tag.key == 'sample':
                            sample = tag.value
                        elif tag.key == 'missing_value':
                            missing_value = tag.value

                if batch and sample:
                    sample_tuple = (batch, sample)

                    # Determine which data types this sample has
                    # Parse missing types (empty string means no missing data for basic types)
                    missing_types = [t.strip() for t in missing_value.split(',') if t.strip()] if missing_value else []

                    # Debug logging
                    self.log_info_message(f"DEBUG - Sample {batch}/{sample}:")
                    self.log_info_message(f"  missing_value tag: '{missing_value}'")
                    self.log_info_message(f"  missing_types parsed: {missing_types}")

                    # Add to sets for data types that are NOT missing
                    if 'info' not in missing_types:
                        sample_sets['info'].add(sample_tuple)
                        self.log_info_message(f"  ✓ Added to info")
                    if 'raw_data' not in missing_types:
                        sample_sets['raw_data'].add(sample_tuple)
                        self.log_info_message(f"  ✓ Added to raw_data")
                    if 'follow_up' not in missing_types and 'follow_up_empty' not in missing_types:
                        sample_sets['follow_up'].add(sample_tuple)
                        self.log_info_message(f"  ✓ Added to follow_up")

        # Create Venn diagram
        venn_diagram = None
        if any(len(s) > 0 for s in sample_sets.values()):
            self.log_info_message(f"\nDEBUG - Final sample_sets:")
            self.log_info_message(f"  info: {sample_sets['info']}")
            self.log_info_message(f"  raw_data: {sample_sets['raw_data']}")
            self.log_info_message(f"  follow_up: {sample_sets['follow_up']}")
            fig = create_venn_diagram_3_sets(sample_sets)
            venn_diagram = PlotlyResource(fig)

        # Process medium_table to convert numeric columns to float
        medium_table_processed = self._process_medium_table(medium_table)

        return {
            'resource_set': res,
            'venn_diagram': venn_diagram,
            'medium_table': medium_table_processed
        }

    def _create_ml_data_table(self, full_info_dict: Dict[str, Any], medium_df: pd.DataFrame,
                              raw_data_df: pd.DataFrame, follow_up_dict: Dict[str, Table]) -> Table:
        """
        Create a single ML data table for machine learning.

        The table contains:
        - experiment_id as first column (ESSAI_FERMENTEUR_MILIEU)
        - All medium composition columns (prefix: medium_)
        - All follow-up columns: initial values (prefix: alpha_) and final values (prefix: final_followup_)
        - All raw_data columns: constant values (prefix: constant_) and final values (prefix: final_)

        Args:
            full_info_dict: Dictionary with experiment information
            medium_df: DataFrame with medium composition
            raw_data_df: DataFrame with raw measurement data
            follow_up_dict: Dictionary with follow-up tables

        Returns:
            Table with all ML data
        """
        ml_rows = []

        for essai, fermentors in full_info_dict.items():
            for fermentor, data in fermentors.items():
                # Skip experiments without a medium
                medium = data.get('medium', '')
                if not medium or medium is None:
                    continue

                # Create experiment identifier by combining batch, sample and medium
                experiment_id = f"{essai}_{fermentor}_{medium}"

                # Initialize row
                ml_row = {
                    'experiment_id': experiment_id
                }

                # Add medium composition
                if 'MILIEU' in medium_df.columns:
                    medium_row = medium_df[medium_df['MILIEU'] == medium]
                    if not medium_row.empty:
                        # Add all columns except MILIEU
                        for col in medium_row.columns:
                            if col != 'MILIEU':
                                value = medium_row[col].iloc[0]
                                # Convert to numeric if possible
                                ml_row[f'medium_{col}'] = self._to_numeric(value)

                # Add follow-up data (both initial and final values)
                follow_up_key = f"{essai} {fermentor}"
                if follow_up_key in follow_up_dict:
                    follow_up_df = follow_up_dict[follow_up_key].get_data()
                    if not follow_up_df.empty:
                        # Process each numeric column
                        for col in follow_up_df.columns:
                            # Skip time column and identifier columns
                            if col in ['Temps (h)', 'Temps de culture (h)', 'ESSAI', 'FERMENTEUR', 'MILIEU']:
                                continue

                            # Get first value (alpha/t0)
                            first_value = follow_up_df[col].iloc[0]
                            if pd.notna(first_value):
                                numeric_value = self._to_numeric(first_value)
                                ml_row[f'alpha_{col}'] = numeric_value

                            # Get last non-NaN value (final)
                            col_values = pd.to_numeric(follow_up_df[col], errors='coerce')
                            non_nan_values = col_values.dropna()
                            if len(non_nan_values) > 0:
                                last_value = non_nan_values.iloc[-1]
                                ml_row[f'final_followup_{col}'] = last_value

                # Process raw_data for all columns
                raw_df = data.get('raw_data', pd.DataFrame())
                if not raw_df.empty:
                    for col in raw_df.columns:
                        # Skip identifier and time columns
                        if col in ['ESSAI', 'FERMENTEUR', 'MILIEU', 'Temps de culture (h)', 'Temps (h)']:
                            continue

                        # Check if column is constant (all values are the same)
                        col_values = pd.to_numeric(raw_df[col], errors='coerce')
                        non_nan_values = col_values.dropna()

                        if len(non_nan_values) == 0:
                            # Column is all NaN, skip it
                            continue
                        elif len(non_nan_values.unique()) == 1:
                            # Constant column - add the constant value
                            ml_row[f'constant_{col}'] = non_nan_values.iloc[0]
                        else:
                            # Non-constant column - add the final value
                            last_value = non_nan_values.iloc[-1]
                            ml_row[f'final_{col}'] = last_value

                # Add row to list
                ml_rows.append(ml_row)

        # Create DataFrame
        ml_df = pd.DataFrame(ml_rows)

        # Remove columns that only contain NaN or 0 (except experiment_id)
        cols_to_remove = []
        for col in ml_df.columns:
            if col == 'experiment_id':
                continue

            col_values = pd.to_numeric(ml_df[col], errors='coerce')
            non_nan_values = col_values.dropna()

            # Remove if all NaN or all values are 0
            if len(non_nan_values) == 0 or (non_nan_values == 0).all():
                cols_to_remove.append(col)

        # Drop the columns
        if cols_to_remove:
            ml_df = ml_df.drop(columns=cols_to_remove)

        # Create Table
        ml_table = Table(ml_df)
        ml_table.name = "Machine Learning Data"

        return ml_table

    def _process_medium_table(self, medium_table: Table) -> Table:
        """
        Process the medium table to convert numeric columns to float.

        The first column (MILIEU) is kept as string.
        All other columns are converted to float, handling both comma and dot as decimal separator.
        NaN values are replaced with 0.

        Args:
            medium_table: Input table from medium CSV file

        Returns:
            Processed table with proper data types
        """
        # Get DataFrame from table
        df = medium_table.get_data().copy()

        if df.empty:
            return medium_table

        # Get column names
        columns = df.columns.tolist()

        if not columns:
            return medium_table

        # First column should stay as string (MILIEU)
        # All other columns should be converted to float
        for col_idx, col_name in enumerate(columns):
            if col_idx == 0:
                # Keep first column as string
                continue
            else:
                # Convert to numeric for all other columns
                df[col_name] = df[col_name].apply(self._to_numeric)

        # Replace NaN with 0 for all numeric columns
        df.fillna(0, inplace=True)

        # Create new table with processed data
        processed_table = Table(df)
        processed_table.name = medium_table.name

        return processed_table

    def _to_numeric(self, value) -> float:
        """
        Convert a value to numeric (float), handling special cases.

        - Handles 'x' or 'X' as 0
        - Converts comma to dot for decimal separator
        - Returns 0 for empty or invalid values

        Args:
            value: Value to convert (can be string, number, etc.)

        Returns:
            Float value or 0 for invalid/empty values
        """
        if pd.isna(value) or value == '':
            return 0.0

        value_str = str(value).strip().lower()

        if value_str == 'x' or value_str == '':
            return 0.0

        # Replace comma with dot for decimal separator
        value_str = value_str.replace(',', '.')

        try:
            return float(value_str)
        except ValueError:
            return 0.0
