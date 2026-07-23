<p align="center">
  <img src="https://constellab.space/assets/fl-logo/constellab-logo-text-white.svg" alt="Constellab Logo" width="80%">
</p>

<br/>

# 👋 Welcome to GWS Plate reader 

```gws_plate_reader``` is a [Constellab](https://constellab.io) library (called bricks) developped by [Gencovery](https://gencovery.com/). GWS stands for Gencovery Web Services.

## 🚀 What is Constellab?


✨ [Gencovery](https://gencovery.com/) is a software company that offers [Constellab](https://constellab.io)., the leading open and secure digital infrastructure designed to consolidate data and unlock its full potential in the life sciences industry. Gencovery's mission is to provide universal access to data to enhance people's health and well-being.

🌍 With our Fair Open Access offer, you can use Constellab for free. [Sign up here](https://constellab.space/). Find more information about the Open Access offer here (link to be defined).


## ✅ Features

Gencovery brick to connect to plate reader equipment, parse and quality-check cultivation data, and analyse and visualize growth/cell-culture experiments in Constellab. It supports the BioLector XT and Tecan equipment.
- Connect directly to a BioLector XT device (list/upload protocols, start/stop/pause/resume runs, download finished experiments) through an interactive Streamlit dashboard, with a mock service for development without a physical instrument
- Parse raw BioLector XT (CSV export) or Tecan plate-reader data, together with a plate layout, into per-well tables, with QC visualizations (data-coverage Venn diagrams) of well/medium/label coverage
- Manage microplate layouts with an interactive dashboard for assigning lab tags to wells (click-select, or whole rows/columns)
- Extract growth-curve features by fitting sigmoid growth models (Logistic, Gompertz, Modified Gompertz, Richards, Weibull, Baranyi-Roberts) or by non-parametric spline-based growth-rate inference
- Quality-check and prepare cell-culture data: outlier/range/missing-data detection, subsampling with configurable interpolation (linear, cubic, pchip, akima, spline, …), and merging feature/metadata tables for downstream analysis (e.g. UMAP)
- Run PCA on culture medium composition tables, with scores, PC1/PC2 scatter and biplot visualizations
- Explore experiments through interactive dashboards: per-observer table/plot/growth-rate analysis views for BioLector and Tecan data, and a full bioprocess dashboard (file upload, automated processing, QC, multi-chart visualization, descriptive stats, batch comparison)


## 📄 Documentation

📄  For `gws_plate_reader` brick documentation, click [here](https://constellab.community/bricks/gws_plate_reader/latest/doc/getting-started/25300a24-a42b-408c-87ea-73dbe7ab249a)

💫 For Constellab application documentation, click [here](https://constellab.community/bricks/gws_academy/latest/doc/getting-started/b38e4929-2e4f-469c-b47b-f9921a3d4c74)

## 🛠️ Installation

The `gws_plate_reader` brick requires the `gws_core` brick.

### 🔥 Recommended Method

The best way to install a brick is through the Constellab platform. With our Fair Open Access offer, you get a free cloud data lab where you can install bricks directly. [Sign up here](https://constellab.space/)

Learn about the data lab here : [Overview](https://constellab.community/bricks/gws_academy/latest/doc/digital-lab/overview/294e86b4-ce9a-4c56-b34e-61c9a9a8260d) and [Data lab management](https://constellab.community/bricks/gws_academy/latest/doc/digital-lab/on-cloud-digital-lab-management/4ab03b1f-a96d-4d7a-a733-ad1edf4fb53c)

### 🔧 Manual installation

This section is for users who want to install the brick manually. It can also be used to install the brick manually in the Constellab Codelab.

We recommend installing using Ubuntu 22.04 with python 3.10.

Required packages are listed in the ```settings.json``` file, for now the packages must be installed manually.

```bash 
pip install grpcio==1.64.1 streamlit-extras==0.4.7
```


#### Usage


▶️ To start the server :

```bash
gws server run
```

🕵️ To run a given unit test

```bash
gws server test [TEST_FILE_NAME]
```

Replace `[TEST_FILE_NAME]` with the name of the test file (without `.py`) in the tests folder. Execute this command in the folder of the brick.

🕵️ To run the whole test suite, use the following command:

```bash
gws server test all
```

📌 VSCode users can use the predefined run configuration in `.vscode/launch.json`.

## 🤗 Community

🌍 Join the Constellab community [here](https://constellab.community/) to share and explore stories, code snippets and bricks with other users.

🚩 Feel free to open an issue if you have any question or suggestion.

☎️ If you have any questions or suggestions, please feel free to contact us through our website: [Constellab](https://constellab.io/).

## 🌎 License

```gws_plate_reader``` is completely free and open-source and licensed under the [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).

<br/>


This brick is maintained with ❤️ by [Gencovery](https://gencovery.com/).

<p align="center">
  <img src="https://framerusercontent.com/images/Z4C5QHyqu5dmwnH32UEV2DoAEEo.png?scale-down-to=512" alt="Gencovery Logo"  width="30%">
</p>