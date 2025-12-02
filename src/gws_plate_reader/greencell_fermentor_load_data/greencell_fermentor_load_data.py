import os
import re

import pandas as pd
import numpy as np
import plotly.graph_objects as go

from gws_core import (File, InputSpec, OutputSpec, InputSpecs, OutputSpecs, Table, Folder, Tag,
                      TypingStyle, ResourceSet, Task, task_decorator, TableImporter, ZipCompress,
                      PlotlyResource)

from typing import Dict, Any, Set, Tuple


def create_venn_diagram_2_sets(sample_sets: Dict[str, Set[Tuple[str, str]]]) -> go.Figure:
    """
    Create a Venn diagram with 2 overlapping circles representing data types
    (info, follow_up) showing all intersections.

    Args:
        sample_sets: Dict with sets of (batch, sample) tuples for each data type
            Keys: 'info', 'follow_up'
            Values: Set of (batch, sample) tuples

    Returns:
        Plotly Figure with the Venn diagram showing all intersections
    """

    # Extract sets
    A = sample_sets.get('info', set())  # Info
    B = sample_sets.get('follow_up', set())  # Follow-up

    # Calculate all regions
    only_A = len(A - B)  # Only Info
    only_B = len(B - A)  # Only Follow-up
    A_and_B = len(A & B)  # Both (complete samples)

    # Create figure
    fig = go.Figure()

    # Circle parameters
    radius = 0.3
    Ax, Ay = 0.4, 0.5   # Info (left)
    Bx, By = 0.6, 0.5   # Follow-up (right)

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

    # Circle B - Follow-up (Purple)
    x_B = radius * np.cos(theta) + Bx
    y_B = radius * np.sin(theta) + By
    fig.add_trace(go.Scatter(
        x=x_B, y=y_B,
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
    fig.add_annotation(x=Bx, y=By + radius + 0.05, text="<b>Follow-up</b>",
                       showarrow=False, font=dict(size=14))

    # Add region counts (manually positioned for clarity)
    # Only A (Info only)
    fig.add_annotation(x=Ax - 0.15, y=Ay, text=str(only_A),
                       showarrow=False, font=dict(size=14))

    # Only B (Follow-up only)
    fig.add_annotation(x=Bx + 0.15, y=By, text=str(only_B),
                       showarrow=False, font=dict(size=14))

    # A ∩ B (center) - Both (complete)
    fig.add_annotation(
        x=0.5, y=Ay,
        text=f"<b>{A_and_B}</b>",
        showarrow=False,
        font=dict(size=16, color='darkgreen'),
        bgcolor='rgba(255, 255, 255, 0.9)',
        borderpad=4,
        bordercolor='darkgreen',
        borderwidth=2
    )

    # Update layout
    fig.update_layout(
        title="Data Availability - Venn Diagram (Info, Follow-up)", showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False, range=[0, 1]),
        yaxis=dict(
            showticklabels=False, showgrid=False, zeroline=False, range=[0.2, 1.05],
            scaleanchor="x", scaleratio=1),
        height=600, width=600, plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',)

    return fig


@task_decorator("BiolectorLoadData", human_name="Load Biolector data QC0",
                short_description="Load and process Biolector QC0 fermentation data from multiple sources",
                style=TypingStyle.community_icon(icon_technical_name="file-upload", background_color="#2492FE"))
class GreencellFermentorLoadData(Task):
    """
    Load and process Biolector QC0 fermentation data from multiple CSV files and follow-up data.

    ## Overview
    This task integrates data from four different sources to create a comprehensive dataset
    for fermentation analysis. It handles data merging, validation, missing data detection,
    and generates a visual summary of data availability.

    ## Input Files Required

    ### 1. Info CSV (`info_csv`)
    Contains experiment and fermenter information with columns:
    - `ESSAI`: Experiment/trial identifier (e.g., "2 25 211 R3")
    - `FERMENTEUR`: Fermenter identifier (e.g., "5A", "2B")
    - `MILIEU`: Culture medium used (e.g., "Milieu Kluyveromyces x 2")
    - `SOUCHE`: Strain used (e.g., "B667")
    - Additional metadata columns describing experimental conditions

    ### 2. Medium CSV (`medium_csv`)
    Contains culture medium composition with columns:
    - `MILIEU`: Medium identifier (must match Info CSV)
    - Composition columns describing medium components and concentrations

    ### 3. Follow-up ZIP (`follow_up_zip`)
    ZIP file containing CSV files with time-series follow-up data:
    - Each CSV file name corresponds to `<ESSAI>` (without spaces, e.g., "225211R3.csv")
    - First column is time measurement: `Date` or `Temps (h)`
    - Other columns contain temporal measurements with column names indicating the data type and unit (e.g., "Pressure (bar)", "pH (U.pH)")
    - Files starting with "._" (macOS metadata) are automatically ignored

    ## Processing Steps

    1. **File Loading**: Imports all CSV files and the ResourceSet
    2. **Data Indexing**: Creates lookup tables for each (ESSAI, FERMENTEUR) pair
    3. **Follow-up Processing**:
       - Extracts follow-up data for each sample
       - Normalizes decimal formats (comma → dot)
       - Filters negative time values
       - Renames time column to standard format if needed
    4. **Metadata Enrichment**: Adds batch, sample, and medium information as tags
    5. **Missing Data Detection**: Identifies which data types (info/medium/follow_up) are missing for each sample
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
    - **2 Overlapping Circles**: One per data type (Info, Follow-up)
    - **Circle Labels**: Show count of samples with that data type
    - **Center Label**: Shows count of complete samples (both data types present)
    - **Color Coding**:
      - Blue: Info data
      - Purple: Follow-up data

    ### 3. Medium Table (`medium_table`) - Optional
    The medium composition CSV file converted to a Table resource with proper data types:
    - **First column** (MILIEU): Kept as string (medium name/identifier)
    - **Other columns**: Converted to float (handles both comma and dot as decimal separator)
    - **Missing values**: Empty cells or non-numeric text converted to NaN

    ### 4. Metadata Table (`metadata_table`) - Optional
    A Table concatenating medium composition data of the couple and median values of the follow-up data of the sample:
    - **First column** (Series): Contains the 'batch_sample' identifier (e.g., "EPA-WP3-25-001_23A")
    - **Other columns**: Medium composition columns and median values of follow-up measurements

    ## Data Quality

    ### Missing Data Handling
    The task detects and reports missing data through tags:
    - Samples with missing Info will have `missing_value` tag including "info"
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
    [Info CSV] ──┐ ──┼──> FermentalgLoadData ──┬──> [Resource Set] ──> Filter/Analysis
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
             short_description="Medium CSV file with numeric columns properly converted to float", optional=True),
         'metadata_table': OutputSpec(
            Table, human_name="Metadata table",
            short_description="Table containing metadata information", optional=True)
         })

    def run(self, params, inputs):

        info_file: File = inputs['info_csv']
        medium_file: File = inputs['medium_csv']
        follow_up_file: File = inputs['follow_up_zip']

        info_table: Table = TableImporter.call(info_file)
        medium_table: Table = TableImporter.call(medium_file)

        info_table.name = "Info table"
        medium_table.name = "Medium table"

        # Trim ESSAI column to remove leading/trailing spaces
        info_df_temp = info_table.get_data()
        if 'ESSAI' in info_df_temp.columns:
            info_df_temp['ESSAI'] = info_df_temp['ESSAI'].astype(str).str.strip()
            info_table = Table(info_df_temp)
            info_table.name = "Info table"

        # Extract ZIP file to folder
        follow_up_folder_path = os.path.splitext(follow_up_file.path)[0]
        ZipCompress.decompress(follow_up_file.path, follow_up_folder_path)
        follow_up_folder = Folder(follow_up_folder_path)

        follow_up_dict: Dict[str, Table] = {}  # key format: "EssaiSansEspaces"
        follow_up_df_medians = pd.DataFrame()
        couples_follow_up_data = []

        # LOG: Loading follow-up files from folder
        self.log_info_message(f"\n=== FOLLOW-UP FOLDER ===")
        self.log_info_message(f"Follow-up folder path: {follow_up_folder_path}")

        # Les noms de fichiers CSV correspondent à l'ESSAI sans espaces uniquement
        # Exemple: '225246R2.csv' correspond à ESSAI '2 25 246 R2'
        # Le FERMENTEUR n'est PAS dans le nom du fichier
        follow_up_by_essai = {}  # key: "essai_sans_espaces" -> Table

        # Load all CSV files from the follow-up folder
        # List all items in the extracted folder
        for item in follow_up_folder.list_dir():
            item_path = os.path.join(follow_up_folder_path, item)

            # Check if it's a directory (subfolder)
            if os.path.isdir(item_path):
                # It's a subfolder, load CSV files from it
                subfolder = Folder(item_path)
                for file_path in subfolder.list_dir():
                    # Skip macOS metadata files
                    if file_path.startswith('._'):
                        continue

                    file = File(os.path.join(item_path, file_path))
                    table = TableImporter.call(file, params={'delimiter': ','})
                    # Remove file extension from table name
                    table_name = os.path.splitext(file_path)[0]
                    table.name = table_name
                    follow_up_dict[table_name] = table

                    self.log_info_message(f"\nChargement fichier follow_up: '{file_path}' -> table '{table_name}'")
                    # Stocker directement avec la clé (ESSAI sans espaces)
                    follow_up_by_essai[table_name] = table
            elif item.endswith('.csv') and not item.startswith('._'):
                # It's a CSV file directly in the root folder
                file = File(item_path)
                table = TableImporter.call(file, params={'delimiter': ','})
                # Remove file extension from table name
                table_name = os.path.splitext(item)[0]
                table.name = table_name
                follow_up_dict[table_name] = table

                self.log_info_message(f"\nChargement fichier follow_up: '{item}' -> table '{table_name}'")
                # Stocker directement avec la clé (ESSAI sans espaces)
                follow_up_by_essai[table_name] = table

        self.log_info_message(f"Nombre de fichiers follow_up chargés: {len(follow_up_dict)}")
        self.log_info_message(f"Clés des tables follow_up: {list(follow_up_dict.keys())}")

        # Le calcul des médianes se fera plus tard, une fois qu'on aura associé
        # chaque table à ses couples (ESSAI, FERMENTEUR) du fichier info

        full_info_dict: Dict[str, Any] = {}

        info_df: pd.DataFrame = info_table.get_data()
        medium_df: pd.DataFrame = medium_table.get_data()

        # LOG: Afficher les couples du fichier info
        self.log_info_message(f"\n=== FICHIER INFO ===")
        self.log_info_message(f"Nombre de lignes dans info: {len(info_df)}")
        couples_info_list = info_df[['ESSAI', 'FERMENTEUR']].drop_duplicates()
        self.log_info_message(f"Couples distincts dans info:")
        for _, row in couples_info_list.head(10).iterrows():  # Afficher seulement les 10 premiers
            self.log_info_message(f"  ESSAI='{row['ESSAI']}', FERMENTEUR='{row['FERMENTEUR']}'")
        if len(couples_info_list) > 10:
            self.log_info_message(f"  ... et {len(couples_info_list) - 10} autres couples")

        # Créer un mapping entre (ESSAI avec espaces, FERMENTEUR) et les tables follow_up
        # Les clés du ResourceSet correspondent à l'ESSAI sans espaces uniquement
        follow_up_lookup = {}  # key: (essai_avec_espaces, fermenteur) -> Table

        self.log_info_message(f"\n=== MATCHING INFO <-> FOLLOW-UP ===")

        # Maintenant associer chaque couple (ESSAI, FERMENTEUR) à sa table
        # Les noms de fichiers peuvent avoir des suffixes (ex: 224325F1C pour ESSAI '2 24 325 F1')
        for _, row in info_df.iterrows():
            essai = row['ESSAI']
            fermenteur = row['FERMENTEUR']
            essai_sans_espaces = essai.replace(' ', '').strip()

            # Chercher un fichier dont le nom commence par essai_sans_espaces
            for file_key in follow_up_by_essai.keys():
                if file_key.startswith(essai_sans_espaces):
                    # La table follow_up existe pour cet ESSAI (elle contient tous les fermenteurs)
                    follow_up_lookup[(essai, fermenteur)] = follow_up_by_essai[file_key]
                    couples_follow_up_data.append({'ESSAI': essai, 'FERMENTEUR': fermenteur})
                    break  # Un seul fichier par ESSAI

        self.log_info_message(f"\n=== RÉSULTAT MATCHING ===")
        self.log_info_message(f"Nombre de couples (ESSAI, FERMENTEUR) avec follow-up: {len(follow_up_lookup)}")
        self.log_info_message(f"Couples matchés: {[(e, f) for (e, f) in follow_up_lookup.keys()][:10]}")

        # LOG: Liste des series avec follow-up et leur medium
        self.log_info_message(f"\n=== SERIES AVEC FOLLOW-UP ===")
        for (essai, fermenteur) in follow_up_lookup.keys():
            # Normaliser les underscores multiples en un seul
            serie = f"{essai.replace(' ', '_')}_{fermenteur}"
            serie = re.sub(r'_+', '_', serie)  # Remplacer plusieurs _ par un seul
            # Récupérer le medium depuis full_info_dict si disponible
            medium = "UNKNOWN"
            if essai in full_info_dict and fermenteur in full_info_dict[essai]:
                medium = full_info_dict[essai][fermenteur].get('medium', 'UNKNOWN')
            self.log_info_message(f"  Serie: {serie}, Medium: {medium}")

        # Calculer les médianes pour chaque couple (ESSAI, FERMENTEUR) qui a un follow-up
        self.log_info_message(f"\n=== CALCUL DES MÉDIANES FOLLOW-UP ===")
        for (essai, fermenteur), follow_up_table in follow_up_lookup.items():
            df = follow_up_table.get_data()

            # Normaliser les underscores multiples en un seul
            serie = f"{essai.replace(' ', '_')}_{fermenteur}"
            serie = re.sub(r'_+', '_', serie)  # Remplacer plusieurs _ par un seul
            self.log_info_message(f"\n=== Calcul médianes pour {serie} ===")
            self.log_info_message(f"  Shape du DataFrame: {df.shape}")
            self.log_info_message(f"  TOUTES les colonnes du DataFrame follow-up:")
            for i, col in enumerate(df.columns):
                self.log_info_message(f"    [{i}] '{col}'")
            if len(df) > 0:
                self.log_info_message(f"  Première ligne de données: {df.iloc[0].tolist()[:5]}...")

            # Convertir en numérique - mais garder les noms de colonnes originaux
            df_numeric = df.apply(pd.to_numeric, errors="coerce")

            # Filtrer sur Temps >= 25 si la colonne existe ET est numérique
            # Pour les colonnes Date (string), on garde toutes les lignes
            time_col = None
            if 'Temps (h)' in df_numeric.columns:
                # Vérifier que la colonne a des valeurs numériques valides
                if df_numeric['Temps (h)'].notna().any():
                    time_col = 'Temps (h)'

            if time_col:
                original_len = len(df_numeric)
                df_numeric = df_numeric[df_numeric[time_col] >= 25]
                self.log_info_message(f"  Filtre {time_col} >= 25: {len(df_numeric)}/{original_len} lignes restantes")
            else:
                # Pas de colonne de temps numérique - garder toutes les lignes
                self.log_info_message(f"  Pas de filtre temporel - utilisation de toutes les {len(df_numeric)} lignes")

            # Calculer les médianes - cela retourne une Series avec les noms de colonnes comme index
            medians = df_numeric.median(numeric_only=True)

            # Créer un dictionnaire avec les médianes
            median_dict = medians.to_dict()
            # Normaliser les underscores multiples en un seul
            serie_normalized = f"{essai.replace(' ', '_')}_{fermenteur}"
            median_dict["Series"] = re.sub(r'_+', '_', serie_normalized)

            # Créer un DataFrame avec une seule ligne
            median_row = pd.DataFrame([median_dict])

            self.log_info_message(
                f"  Médianes calculées: {len(median_dict)-1} valeurs, Series='{median_dict['Series']}'")
            self.log_info_message(f"  Colonnes des médianes: {list(median_row.columns)[:10]}...")

            follow_up_df_medians = pd.concat([follow_up_df_medians, median_row], ignore_index=True)

        # Nettoyer follow_up_df_medians
        self.log_info_message(f"\n=== NETTOYAGE MÉDIANES ===")
        self.log_info_message(
            f"Avant nettoyage: {len(follow_up_df_medians)} lignes, {len(follow_up_df_medians.columns) if not follow_up_df_medians.empty else 0} colonnes")

        if not follow_up_df_medians.empty:
            follow_up_df_medians.columns = follow_up_df_medians.columns.str.strip()
            # Supprimer les colonnes de temps si elles existent
            time_cols_to_drop = [col for col in follow_up_df_medians.columns if col in ['Temps (h)', 'Date']]
            if time_cols_to_drop:
                self.log_info_message(f"Suppression colonnes temps: {time_cols_to_drop}")
                follow_up_df_medians = follow_up_df_medians.drop(time_cols_to_drop, axis=1)

            # Ne PAS supprimer les lignes avec des NaN - chaque fichier a ses propres colonnes
            # (ex: fichier 1 a '1SP1 (Rpm)', fichier 2 a '2SP1 (Rpm)', donc chaque ligne aura des NaN)
            # On garde toutes les lignes tant qu'elles ont une colonne 'Series'
            self.log_info_message(f"Colonnes disponibles: {list(follow_up_df_medians.columns)[:15]}...")

            # Vérifier que la colonne Series existe
            if 'Series' not in follow_up_df_medians.columns:
                self.log_info_message(f"⚠️ ERREUR: Colonne 'Series' manquante!")
            else:
                self.log_info_message(f"Series values: {follow_up_df_medians['Series'].tolist()}")

            self.log_info_message(
                f"Après nettoyage: {len(follow_up_df_medians)} lignes, {len(follow_up_df_medians.columns)} colonnes")
            self.log_info_message(f"Colonnes finales: {list(follow_up_df_medians.columns)[:10]}...")
        else:
            self.log_info_message(f"DataFrame médianes est VIDE - aucun couple avec follow-up trouvé")

        # Récupérer tous les couples distincts (info uniquement, follow_up est déjà associé)
        couples_info = info_df[['ESSAI', 'FERMENTEUR']].drop_duplicates()

        # Utiliser uniquement couples_info car on a déjà matché follow_up avec info
        tous_couples = couples_info.copy()

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

            # Récupérer les medium_data si le medium existe
            if full_info_dict[essai][fermentor]['medium'] is not None and 'MILIEU' in medium_df.columns:
                medium_data_filtered = medium_df[medium_df['MILIEU'] == full_info_dict[essai][fermentor]['medium']]
                medium_data_filtered = medium_data_filtered.drop(columns=['MILIEU'])
                full_info_dict[essai][fermentor]['medium_data'] = medium_data_filtered
            else:
                full_info_dict[essai][fermentor]['medium_data'] = pd.DataFrame()

            # Vérifier si un fichier de suivi existe pour ce couple en utilisant le lookup
            lookup_key = (essai, fermentor)
            full_info_dict[essai][fermentor]['has_follow_up'] = lookup_key in follow_up_lookup
            if lookup_key in follow_up_lookup:
                full_info_dict[essai][fermentor]['follow_up_table'] = follow_up_lookup[lookup_key]
                self.log_info_message(f"Fichier de suivi trouvé pour {essai} {fermentor}")
            else:
                full_info_dict[essai][fermentor]['follow_up_table'] = Table(pd.DataFrame())
                self.log_info_message(f"Aucun fichier de suivi pour {essai} {fermentor}")

        res: ResourceSet = ResourceSet()

        for essai, fermentors in full_info_dict.items():
            for fermentor, data in fermentors.items():
                try:
                    # Utiliser les informations stockées dans full_info_dict
                    follow_up_df: pd.DataFrame = data['follow_up_table'].get_data()

                    # Traiter uniquement les follow_up data (pas de merge avec raw_data)
                    if not follow_up_df.empty:
                        # Convertir la colonne Date en temps numérique (heures depuis le début)
                        if 'Date' in follow_up_df.columns:
                            try:
                                # Parser les dates (format: 'DD/MM/YYYY HH:MM' ou similaire)
                                follow_up_df['Date_parsed'] = pd.to_datetime(
                                    follow_up_df['Date'],
                                    format='%d/%m/%Y %H:%M', errors='coerce')

                                # Si le parsing a échoué, essayer d'autres formats courants
                                if follow_up_df['Date_parsed'].isna().all():
                                    follow_up_df['Date_parsed'] = pd.to_datetime(follow_up_df['Date'], errors='coerce')

                                # Calculer le temps en heures depuis la première date
                                if not follow_up_df['Date_parsed'].isna().all():
                                    first_date = follow_up_df['Date_parsed'].min()
                                    time_delta = follow_up_df['Date_parsed'] - first_date
                                    follow_up_df['Temps de culture (h)'] = time_delta.dt.total_seconds() / 3600

                                    # Supprimer la colonne temporaire et la colonne Date originale
                                    follow_up_df = follow_up_df.drop(columns=['Date_parsed', 'Date'])

                                    self.log_info_message(
                                        f"  ✅ Colonne Date convertie en 'Temps de culture (h)' (0 à {follow_up_df['Temps de culture (h)'].max():.2f}h)")
                                else:
                                    # Si le parsing a complètement échoué, supprimer juste la colonne Date
                                    follow_up_df = follow_up_df.drop(columns=['Date_parsed', 'Date'])
                                    self.log_info_message(
                                        f"  ⚠️ Impossible de parser la colonne Date, colonne supprimée")
                            except Exception as e:
                                self.log_info_message(f"  ⚠️ Erreur lors de la conversion Date: {str(e)}")
                                # En cas d'erreur, supprimer la colonne Date
                                if 'Date' in follow_up_df.columns:
                                    follow_up_df = follow_up_df.drop(columns=['Date'])

                        # Renommer la colonne de temps si elle existe déjà sous un autre nom
                        elif 'Temps (h)' in follow_up_df.columns:
                            follow_up_df = follow_up_df.rename(columns={'Temps (h)': 'Temps de culture (h)'})
                            self.log_info_message(f"  ✅ Colonne 'Temps (h)' renommée en 'Temps de culture (h)'")

                        # Normaliser le format et filtrer les temps négatifs si on a une colonne de temps
                        if 'Temps de culture (h)' in follow_up_df.columns:
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
                            original_len = len(follow_up_df)
                            follow_up_df = follow_up_df[follow_up_df['Temps de culture (h)'] >= 0]
                            if len(follow_up_df) < original_len:
                                self.log_info_message(
                                    f"  Filtré {original_len - len(follow_up_df)} lignes avec temps < 0")

                        full_df = follow_up_df.copy()
                    else:
                        # Aucune donnée temporelle (pas de follow_up)
                        # Créer un DataFrame avec juste les infos si elles existent
                        if not data['info'].empty:
                            full_df = data['info'].copy()
                        else:
                            full_df = pd.DataFrame()

                    # Créer une Table pour chaque couple (essai, fermentor)
                    # même si full_df est vide, pour avoir les tags batch/sample dans le ResourceSet
                    if not full_df.empty or not data['info'].empty:
                        self.log_info_message(f"\n=== Création table pour {essai} {fermentor} ===")
                        self.log_info_message(f"  Shape initial: {full_df.shape if not full_df.empty else '(0,0)'}")
                        self.log_info_message(f"  Colonnes: {list(full_df.columns) if not full_df.empty else []}")

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
                            self.log_info_message(
                                f"  Colonnes vides supprimées ({len(removed_columns)}): {removed_columns[:5]}...")

                        self.log_info_message(
                            f"  Colonnes restantes ({len(columns_to_keep)}): {columns_to_keep[:10]}...")

                        # Vérifier si le DataFrame n'est pas complètement vide après suppression des colonnes
                        if full_df.empty or len(columns_to_keep) == 0:
                            self.log_info_message(f"  ⚠️ Aucune donnée valide, SKIP création table")
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

                        # LOG: Debug missing value detection
                        self.log_info_message(f"\n=== MISSING VALUE CHECK for {essai} {fermentor} ===")

                        # Vérifier si les informations (info) manquent
                        if data['info'].empty:
                            missing_values.append('info')
                            self.log_info_message(f"  ❌ Info is EMPTY")
                        else:
                            self.log_info_message(f"  ✅ Info OK ({len(data['info'])} rows)")

                        # Vérifier si les données de medium manquent
                        if data['medium'] is None or data['medium_data'].empty:
                            missing_values.append('medium')
                            self.log_info_message(
                                f"  ❌ Medium is MISSING (medium={data['medium']}, data_empty={data['medium_data'].empty})")
                        else:
                            self.log_info_message(f"  ✅ Medium OK ({data['medium']})")

                        # Vérifier si les fichiers de suivi manquent
                        lookup_key = (essai, fermentor)
                        has_follow_up_file = lookup_key in follow_up_lookup

                        # Vérifier l'état du fichier de suivi
                        if not has_follow_up_file:
                            # Pas de fichier de suivi du tout
                            missing_values.append('follow_up')
                            self.log_info_message(f"  ❌ Follow-up file NOT FOUND")
                        else:
                            # Le fichier existe, vérifier s'il est vide
                            follow_up_data = follow_up_lookup[lookup_key].get_data()
                            if follow_up_data.empty:
                                missing_values.append('follow_up_empty')
                                self.log_info_message(f"  ❌ Follow-up file is EMPTY")
                            else:
                                self.log_info_message(
                                    f"  ✅ Follow-up OK ({len(follow_up_data)} rows, {len(follow_up_data.columns)} columns)")

                        # Ajouter le tag missing_value si des données manquent
                        self.log_info_message(f"  Final missing_values: {missing_values}")
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
                    if 'follow_up' not in missing_types and 'follow_up_empty' not in missing_types:
                        sample_sets['follow_up'].add(sample_tuple)
                        self.log_info_message(f"  ✓ Added to follow_up")

        # Create Venn diagram
        venn_diagram = None
        if any(len(s) > 0 for s in sample_sets.values()):
            self.log_info_message(f"\nDEBUG - Final sample_sets:")
            self.log_info_message(f"  info: {sample_sets['info']}")
            self.log_info_message(f"  follow_up: {sample_sets['follow_up']}")
            fig = create_venn_diagram_2_sets(sample_sets)
            venn_diagram = PlotlyResource(fig)

        # Process medium_table to convert numeric columns to float
        medium_table_processed = self._process_medium_table(medium_table)

        # LOG: Count tables without missing_value tag
        self.log_info_message(f"\n=== STATISTIQUES RESOURCE SET ===")
        tables_without_missing = 0
        tables_with_missing = 0
        for resource_name, resource in res.get_resources().items():
            if isinstance(resource, Table):
                has_missing = False
                if hasattr(resource, 'tags') and resource.tags:
                    for tag in resource.tags.get_tags():
                        if tag.key == 'missing_value':
                            has_missing = True
                            tables_with_missing += 1
                            break
                if not has_missing:
                    tables_without_missing += 1

        self.log_info_message(f"Total tables: {len(res.get_resources())}")
        self.log_info_message(f"Tables SANS missing_value tag: {tables_without_missing}")
        self.log_info_message(f"Tables AVEC missing_value tag: {tables_with_missing}")

        metadata_table = self._create_metadata_data_table(
            full_info_dict, medium_df, follow_up_df_medians
        )

        return {
            'resource_set': res,
            'venn_diagram': venn_diagram,
            'medium_table': medium_table_processed,
            'metadata_table': metadata_table
        }

    def _create_metadata_data_table(self, full_info_dict: Dict[str, Any], medium_df: pd.DataFrame,
                                    follow_up_medians_df: pd.DataFrame) -> Table:
        """
        Create a metadata DataFrame for machine learning purposes.
        """
        self.log_info_message(f"\n=== CRÉATION METADATA TABLE ===")
        self.log_info_message(
            f"follow_up_medians_df: {len(follow_up_medians_df)} lignes, {len(follow_up_medians_df.columns) if not follow_up_medians_df.empty else 0} colonnes")
        if not follow_up_medians_df.empty:
            self.log_info_message(f"Colonnes médianes: {list(follow_up_medians_df.columns)[:10]}...")
            self.log_info_message(
                f"Series dans médianes: {follow_up_medians_df['Series'].tolist() if 'Series' in follow_up_medians_df.columns else 'NO SERIES COLUMN'}")

        metadata_rows = []

        for essai, fermentors in full_info_dict.items():
            for fermentor, data in fermentors.items():
                # Skip experiments without a medium
                medium = data.get('medium', '')
                if not medium or medium is None:
                    self.log_info_message(f"Skip {essai}_{fermentor}: pas de medium")
                    continue

                # Create experiment identifier by combining batch, sample and medium
                # Use underscores consistently to match the Series in medians DataFrame
                serie = f"{essai.replace(' ', '_')}_{fermentor}"
                # Normaliser les underscores multiples en un seul
                serie = re.sub(r'_+', '_', serie)

                self.log_info_message(f"\nTraitement {serie}, medium={medium}")

                # Initialize row
                metadata_row = {
                    'Series': serie,
                    'Medium': medium
                }

                # Add medium composition
                if 'MILIEU' in medium_df.columns:
                    # Matching case-insensitive pour éviter les problèmes de casse
                    medium_row = medium_df[medium_df['MILIEU'].str.lower() == medium.lower()]
                    if not medium_row.empty:
                        # Add all columns except MILIEU
                        for col in medium_row.columns:
                            if col != 'MILIEU':
                                value = medium_row[col].iloc[0]
                                # Convert to numeric if possible
                                metadata_row[col] = self._to_numeric(value)
                        self.log_info_message(f"  Ajouté {len(medium_row.columns)-1} colonnes de medium composition")
                    else:
                        self.log_info_message(f"  ⚠️ Medium '{medium}' non trouvé dans medium_df")

                # Add follow-up medians
                follow_up_median_row = follow_up_medians_df[follow_up_medians_df['Series'] == serie]
                if not follow_up_median_row.empty:
                    added_count = 0
                    for col in follow_up_median_row.columns:
                        if col != 'Series':
                            value = follow_up_median_row[col].iloc[0]
                            # Only add non-NaN values
                            if pd.notna(value):
                                metadata_row[col] = self._to_numeric(value)
                                added_count += 1
                    self.log_info_message(
                        f"  ✅ Ajouté {added_count} colonnes de médianes follow-up (non-NaN)")
                else:
                    self.log_info_message(f"  ⚠️ Pas de médianes follow-up pour '{serie}'")

                metadata_rows.append(metadata_row)

        self.log_info_message(f"\n{len(metadata_rows)} lignes créées pour metadata table")

        # Create DataFrame
        metadata_df = pd.DataFrame(metadata_rows)

        # Remove columns that only contain NaN or 0 (except experiment_id)
        cols_to_remove = []
        for col in metadata_df.columns:
            if col == 'Series' or col == 'Medium':
                continue
            col_values = pd.to_numeric(metadata_df[col], errors='coerce')
            non_nan_values = col_values.dropna()

            # Remove if all NaN or all values are 0
            if len(non_nan_values) == 0 or (non_nan_values == 0).all():
                cols_to_remove.append(col)

        # Drop the columns
        if cols_to_remove:
            metadata_df = metadata_df.drop(columns=cols_to_remove)

        # Create Table
        metadata_table = Table(metadata_df)
        metadata_table.name = "Metadata Table"

        return metadata_table

    def _get_follow_up_df_medians(self, batch: str, sample: str, follow_up_df: pd.DataFrame) -> pd.DataFrame:
        """
        Get the median values for each column in the follow-up DataFrame.
        Only for columns after "Temps (h)" >= 25.

        Args:
            follow_up_df: DataFrame with follow-up data

        Returns:
            DataFrame with median values for each column
        """
        df = follow_up_df.copy()
        df = df.apply(pd.to_numeric, errors='coerce')

        if 'Temps (h)' not in df.columns:
            return pd.DataFrame()
        df = df[df['Temps (h)'] >= 25]
        medians = df.median(numeric_only=True)
        medians["Series"] = f"{batch}_{sample}"

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
