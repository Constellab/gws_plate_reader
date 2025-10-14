import os
import re

import pandas as pd

from gws_core import (File, InputSpec, OutputSpec, InputSpecs, OutputSpecs, Table, Folder, Tag,
                      TypingStyle, ResourceSet, Task, task_decorator, TableImporter, ZipCompress)

from typing import Dict, Any, List, Tuple


@task_decorator("FermentalgLoadData", human_name="Load Fermentalg data QC0",
                short_description="Task to load Fermentalg data QC0",
                style=TypingStyle.community_icon(icon_technical_name="file-upload", background_color="#2492FE"))
class FermentalgLoadData(Task):
    """
    Load Fermentalg data QC0.
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
        {
            'resource_set': OutputSpec(ResourceSet, human_name="Resource set containing all the tables")
        }
    )

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

        follow_up_folder_name = follow_up_folder_path.split(os.sep)[-1]

        follow_up_dict: Dict[str, Table] = {}  # key format : "Essai Fermentor"

        for file_path in Folder(f"{follow_up_folder_path}/{follow_up_folder_name}").list_dir():
            file = File(f"{follow_up_folder_path}/{follow_up_folder_name}/{file_path}")
            table = TableImporter.call(file)
            table.name = os.path.splitext(file_path)[0]
            follow_up_dict[table.name] = table

        full_info_dict: Dict[str, Any] = {}

        info_df: pd.DataFrame = info_table.get_data()
        raw_data_df: pd.DataFrame = raw_data_table.get_data()
        medium_df: pd.DataFrame = medium_table.get_data()

        # Récupérer tous les couples distincts des deux tables
        couples_info = info_df[['ESSAI', 'FERMENTEUR']].drop_duplicates()
        couples_raw_data = raw_data_df[['ESSAI', 'FERMENTEUR']].drop_duplicates()

        # Combiner tous les couples distincts (union)
        tous_couples = pd.concat([couples_info, couples_raw_data]).drop_duplicates().reset_index(drop=True)

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
            if full_info_dict[essai][fermentor]['medium'] is not None:
                medium_data_filtered = medium_df[medium_df['MILIEU'] == full_info_dict[essai][fermentor]['medium']]
                full_info_dict[essai][fermentor]['medium_data'] = medium_data_filtered
            else:
                full_info_dict[essai][fermentor]['medium_data'] = pd.DataFrame()

        res: ResourceSet = ResourceSet()

        for essai, fermentors in full_info_dict.items():
            for fermentor, data in fermentors.items():

                row_data_df: pd.DataFrame = data['raw_data']
                follow_up_df: pd.DataFrame = follow_up_dict.get(
                    f"{essai} {fermentor}", Table(pd.DataFrame())).get_data()

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
                    full_df = pd.DataFrame()

                # Créer une Table à partir du DataFrame mergé
                if not full_df.empty:
                    merged_table = Table(full_df)
                    merged_table.name = f"{essai}_{fermentor}"

                    tags = [
                        Tag('batch', essai),
                        Tag('sample', fermentor)
                    ]

                    if data['medium'] is not None:
                        medium_data: Dict = data['medium_data'].to_dict() if not data['medium_data'].empty else {}
                        tags.append(Tag('medium', data['medium'], additional_info={'composed': medium_data}))

                    merged_table.tags.add_tags(tags)

                    for col in merged_table.column_names:

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
                        merged_table.add_column_tag_by_name(col, 'name', column_name)
                        if unit is not None:
                            merged_table.add_column_tag_by_name(col, 'unit', unit)

                    res.add_resource(merged_table)

        return {'resource_set': res}
