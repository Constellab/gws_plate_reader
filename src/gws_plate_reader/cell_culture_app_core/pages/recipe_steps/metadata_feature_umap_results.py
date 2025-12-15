"""
Metadata Feature UMAP Results Display for Cell Culture Dashboard
Displays the results of a Metadata Feature UMAP analysis scenario
"""
import streamlit as st

from gws_core import Scenario, ScenarioStatus, ScenarioProxy, Table
from gws_core.impl.plotly.plotly_resource import PlotlyResource
from gws_plate_reader.cell_culture_app_core.cell_culture_state import CellCultureState
from gws_plate_reader.cell_culture_app_core.cell_culture_recipe import CellCultureRecipe


def render_metadata_feature_umap_results(recipe: CellCultureRecipe, cell_culture_state: CellCultureState,
                                         umap_scenario: Scenario) -> None:
    """
    Render the Metadata Feature UMAP analysis results

    :param recipe: The Recipe instance
    :param cell_culture_state: The cell culture state
    :param umap_scenario: The UMAP scenario to display results for
    """
    translate_service = cell_culture_state.get_translate_service()

    st.title(f"{recipe.name} - {umap_scenario.title}")

    # Check scenario status
    if umap_scenario.status != ScenarioStatus.SUCCESS:
        if umap_scenario.status == ScenarioStatus.ERROR:
            st.error(f"❌ {translate_service.translate('umap_analysis_failed')}")
        elif umap_scenario.status.is_running():
            st.info(f"⏳ {translate_service.translate('umap_analysis_running')}")
        else:
            st.warning(translate_service.translate('umap_analysis_not_completed').format(
                status=umap_scenario.status.name))
        return

    st.success(translate_service.translate('umap_analysis_complete'))

    # Display UMAP scenario outputs
    scenario_proxy = ScenarioProxy.from_existing_scenario(umap_scenario.id)
    protocol_proxy = scenario_proxy.get_protocol()

    # Display merged table info
    st.markdown("### 📊 " + translate_service.translate('combined_data'))
    merged_table = protocol_proxy.get_output('merged_table')
    if merged_table and isinstance(merged_table, Table):
        merged_df = merged_table.get_data()
        n_rows, n_cols = merged_df.shape
        st.info(translate_service.translate('combined_table_info').format(rows=n_rows, cols=n_cols))

        with st.expander(f"📋 {translate_service.translate('preview_combined_table')}"):
            st.dataframe(merged_df.head(20), width='stretch')

            # Download button
            csv = merged_df.to_csv(index=False)
            st.download_button(
                label=f"💾 {translate_service.translate('download_combined_table_csv')}",
                data=csv,
                file_name=f"metadata_features_merged_{umap_scenario.id[:8]}.csv",
                mime="text/csv"
            )
    else:
        st.warning(translate_service.translate('combined_table_unavailable'))

    st.markdown("---")

    # Display 2D UMAP plot
    st.markdown(f"### 🗺️ {translate_service.translate('umap_2d_plot')}")
    st.markdown(translate_service.translate('visualization_2d_description'))

    umap_2d_plot = protocol_proxy.get_output('umap_2d_plot')
    if umap_2d_plot and isinstance(umap_2d_plot, PlotlyResource):
        fig = umap_2d_plot.figure
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Interprétation** :
        - Chaque point = une série (essai/fermenteur)
        - Couleur = milieu de culture
        - Proximité = composition ET comportement de croissance similaires
        - Clusters = groupes de séries avec profils intégrés similaires
        """)
    else:
        st.warning("⚠️ Graphique UMAP 2D non disponible")

    st.markdown("---")

    # Display 3D UMAP plot
    st.markdown(f"### 🎲 Projection UMAP 3D")
    st.markdown("Visualisation en 3 dimensions (permet de mieux distinguer certaines structures)")

    umap_3d_plot = protocol_proxy.get_output('umap_3d_plot')
    if umap_3d_plot and isinstance(umap_3d_plot, PlotlyResource):
        fig = umap_3d_plot.figure
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        **Conseils** :
        - Faites tourner le graphique pour explorer sous différents angles
        - Zoomez pour examiner des zones spécifiques
        - Comparez avec la projection 2D pour une meilleure compréhension
        """)
    else:
        st.warning("⚠️ Graphique UMAP 3D non disponible")

    st.markdown("---")

    # Display 2D coordinates table
    st.markdown(f"### 📊 Coordonnées UMAP 2D")
    umap_2d_table = protocol_proxy.get_output('umap_2d_table')
    if umap_2d_table and isinstance(umap_2d_table, Table):
        df_2d = umap_2d_table.get_data()

        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df_2d, width='stretch', height=400)
        with col2:
            st.metric("Nombre de séries", len(df_2d))
            st.metric("Colonnes", len(df_2d.columns))

            # Show column names
            st.caption("**Colonnes disponibles** :")
            for col in df_2d.columns:
                st.caption(f"- {col}")

        # Download button
        csv = df_2d.to_csv(index=False)
        st.download_button(
            label=f"💾 {translate_service.translate('download_2d_coordinates_csv')}",
            data=csv,
            file_name=f"umap_2d_coordinates_{umap_scenario.id[:8]}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"⚠️ {translate_service.translate('coordinates_2d_table_unavailable')}")

    st.markdown("---")

    # Display 3D coordinates table
    st.markdown(f"### 📊 Coordonnées UMAP 3D")
    umap_3d_table = protocol_proxy.get_output('umap_3d_table')
    if umap_3d_table and isinstance(umap_3d_table, Table):
        df_3d = umap_3d_table.get_data()

        col1, col2 = st.columns([2, 1])
        with col1:
            st.dataframe(df_3d, width='stretch', height=400)
        with col2:
            st.metric("Nombre de séries", len(df_3d))
            st.metric("Colonnes", len(df_3d.columns))

            # Show column names
            st.caption("**Colonnes disponibles** :")
            for col in df_3d.columns:
                st.caption(f"- {col}")

        # Download button
        csv = df_3d.to_csv(index=False)
        st.download_button(
            label=f"💾 {translate_service.translate('download_3d_coordinates_csv')}",
            data=csv,
            file_name=f"umap_3d_coordinates_{umap_scenario.id[:8]}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"⚠️ {translate_service.translate('coordinates_3d_table_unavailable')}")

    # Info box with interpretation guide
    with st.expander(f"💡 Guide d'interprétation détaillé"):
        st.markdown(f"### Comprendre les résultats UMAP")

        st.markdown("""
        #### Que montre cette analyse ?

        Cette analyse UMAP combine **deux types d'informations** :

        1. **Métadonnées (composition)** :
           - Concentrations en nutriments, vitamines, minéraux
           - Formulation du milieu de culture
           - Conditions initiales

        2. **Features (performances)** :
           - Paramètres de croissance (µ, lag, asymptote)
           - Métriques statistiques des fits
           - Intervalles de croissance
           - Temps caractéristiques

        La projection UMAP révèle comment ces deux dimensions sont liées.

        #### Patterns à rechercher

        **1. Clusters de milieux similaires** :
        - Points de même couleur regroupés → milieux de composition proche donnent des résultats similaires
        - Points de couleurs différentes regroupés → compositions différentes, performances similaires (milieux alternatifs !)

        **2. Séries isolées** :
        - Points éloignés → comportements uniques ou aberrants
        - Peuvent indiquer des innovations ou des problèmes

        **3. Gradients** :
        - Transition progressive entre groupes → effet continu d'un paramètre
        - Utile pour identifier des relations dose-réponse

        **4. Forme globale** :
        - Structure en branches → différentes stratégies de croissance
        - Structure en nuage → grande variabilité
        - Plusieurs clusters distincts → catégories bien définies

        #### Applications pratiques

        **Optimisation de milieux** :
        - Identifiez les milieux donnant les meilleures performances (zone spécifique du graphique)
        - Trouvez les caractéristiques communes de ces milieux dans la table combinée
        - Formulez de nouveaux milieux en interpolant dans cette zone

        **Réduction des coûts** :
        - Cherchez des points proches mais de compositions différentes
        - Testez si des ingrédients moins chers donnent des résultats équivalents

        **Contrôle qualité** :
        - Les nouveaux lots doivent tomber dans la même région que les références
        - Les déviations révèlent des problèmes de formulation ou de process

        **Design d'expériences** :
        - Les zones peu explorées méritent investigation
        - Planifiez de nouveaux tests pour remplir les gaps

        #### Limites et précautions

        - UMAP préserve la structure locale mais peut déformer les distances globales
        - La normalisation est cruciale (métadonnées et features ont des échelles très différentes)
        - Plusieurs projections peuvent donner des vues complémentaires
        - Validez toujours les insights avec des tests biologiques

        #### Export et suite de l'analyse

        Utilisez les tables de coordonnées téléchargées pour :
        - Analyser statistiquement les clusters (ANOVA, tests post-hoc)
        - Corréler avec d'autres variables non incluses dans l'UMAP
        - Créer des modèles prédictifs (régression, classification)
        - Communiquer les résultats (les coordonnées sont faciles à visualiser dans d'autres outils)
        """)

        st.markdown("---")

        st.markdown(f"### Paramètres UMAP utilisés")
        st.markdown("""
        Les paramètres UMAP influencent la projection finale :

        - **n_neighbors** : Structure locale (faible) vs globale (élevé)
        - **min_dist** : Dispersion des points
        - **metric** : Définition de la "distance" entre séries
        - **scale_data** : Normalisation préalable (fortement recommandée)

        Si les résultats ne sont pas satisfaisants, essayez avec différents paramètres.
        """)
