# Cell Culture App Core - Common Translations

This directory contains **common translations** shared across all cell culture dashboards.

## Files

- **`fr.json`** - French translations (396 keys)
- **`en.json`** - English translations (394 keys)

## What's Included

These translations are used in all cell culture analysis dashboards:

### Navigation & UI
- Page titles and navigation elements
- Button labels
- Menu items
- Form labels

### Analysis Steps
- Selection
- Quality check
- PCA analysis
- Feature extraction

### Data Visualization
- Chart labels
- Table headers
- Export options
- Download buttons

### Common Messages
- Status messages
- Error messages
- Validation messages
- Help text (generic)

## Usage

These translations are automatically merged with dashboard-specific translations during the build process.

**DO NOT** manually edit translations in the dashboard directories. Always edit:
- Common translations: `cell_culture_app_core/{lang}.json`
- Specific translations: `{dashboard}_dashboard/_*_dashboard_core/{lang}_specific.json`

Then run: `python3 build_translations.py`

## Adding Translations

Add translations here if they are **used by multiple dashboards** or are **generic cell culture concepts**.

Examples of common translations:
```json
{
    "save_table": "Enregistrer la table",
    "quality_check": "Contrôle qualité",
    "pca_analysis": "Analyse PCA",
    "selection_step": "Étape de sélection"
}
```

See `../TRANSLATIONS_README.md` for complete documentation.
