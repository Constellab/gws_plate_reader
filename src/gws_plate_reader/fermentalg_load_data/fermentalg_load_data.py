import os
import re

import pandas as pd

from gws_core import (File, InputSpec, OutputSpec, InputSpecs, OutputSpecs, Table, Folder, Tag,
                      TypingStyle, ResourceSet, Task, task_decorator, TableImporter, ZipCompress)

from typing import Dict, Any


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
                    full_df = pd.DataFrame()

                # Créer une Table à partir du DataFrame mergé
                if not full_df.empty:
                    # Supprimer les colonnes entièrement vides (toutes NaN/None/null/chaînes vides)
                    # Conserver seulement les colonnes qui ont au moins une valeur non-null et non-vide
                    columns_to_keep = []
                    removed_columns = []

                    for col in full_df.columns:
                        # Vérifier si la colonne a au moins une valeur valide
                        col_data = full_df[col]

                        # Conditions pour considérer une colonne comme vide :
                        # 1. Toutes les valeurs sont NaN/None
                        # 2. Toutes les valeurs sont des chaînes vides ou ne contiennent que des espaces
                        # 3. Combinaison des deux

                        is_all_nan = col_data.isna().all()

                        # Pour les colonnes de type object/string, vérifier aussi les chaînes vides
                        if col_data.dtype == 'object':
                            # Remplacer les chaînes vides/espaces par NaN puis vérifier
                            col_cleaned = col_data.astype(str).str.strip().replace('', None)
                            is_all_empty = col_cleaned.isna().all()
                        else:
                            is_all_empty = False

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
                                    print(f"Colonne '{col}' normalisée (virgules -> points) pour {essai}_{fermentor}")
                                # Sinon, garder les valeurs originales (probablement du texte)

                            except Exception as e:
                                # En cas d'erreur, garder les valeurs originales
                                print(f"Impossible de normaliser la colonne '{col}' pour {essai}_{fermentor}: {str(e)}")
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

                    # Vérifier si les fichiers de suivi manquent pour un couple existant dans raw_data
                    # Cette vérification est importante car un couple peut exister dans raw_data mais
                    # ne pas avoir de fichier de suivi correspondant
                    follow_up_key = f"{essai} {fermentor}"
                    has_follow_up_file = follow_up_key in follow_up_dict

                    # Si le couple existe dans raw_data mais n'a pas de fichier de suivi
                    if not data['raw_data'].empty and not has_follow_up_file:
                        missing_values.append('follow_up')

                    # Ou si le fichier de suivi existe mais est vide
                    elif has_follow_up_file:
                        follow_up_data = follow_up_dict[follow_up_key].get_data()
                        if follow_up_data.empty:
                            missing_values.append('follow_up_empty')

                    # Ajouter le tag missing_value si des données manquent
                    if missing_values:
                        tags.append(Tag('missing_value', ', '.join(missing_values)))

                    if data['medium'] is not None:
                        medium_data: Dict = data['medium_data'].to_dict() if not data['medium_data'].empty else {}
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

        return {'resource_set': res}
