# 🌍 Translation System for Cell Culture Dashboards

This directory contains the **common translations** shared across all cell culture dashboard applications (Fermentalg, Biolector, etc.).

## 📁 Structure

```
gws_plate_reader/
├── cell_culture_app_core/          # Common code & translations
│   ├── fr.json                      # 🇫🇷 Common French translations
│   ├── en.json                      # 🇬🇧 Common English translations
│   └── ...
│
├── fermentalg_dashboard/
│   └── _fermentalg_dashboard_core/
│       ├── fr_specific.json         # 🇫🇷 Fermentalg-specific French
│       ├── en_specific.json         # 🇬🇧 Fermentalg-specific English
│       ├── fr.json                  # ⚙️ GENERATED: Merged translations
│       └── en.json                  # ⚙️ GENERATED: Merged translations
│
├── biolector_dashboard/
│   └── _biolector_dashboard_core/
│       ├── fr_specific.json         # 🇫🇷 Biolector-specific French
│       ├── en_specific.json         # 🇬🇧 Biolector-specific English
│       ├── fr.json                  # ⚙️ GENERATED: Merged translations
│       └── en.json                  # ⚙️ GENERATED: Merged translations
│
└── build_translations.py            # 🔨 Build script
```

## 🎯 Translation Types

### Common Translations (`cell_culture_app_core/{lang}.json`)

Generic translations used across **all** cell culture dashboards:
- Navigation elements (pages, buttons, menus)
- Analysis steps (PCA, feature extraction, growth models)
- Quality check terms
- Data visualization labels
- Statistical terms
- Error messages
- Form labels

**Example keys:**
- `create_new_recipe`
- `selection_step`
- `quality_check`
- `medium_pca_analysis`
- `logistic_growth_analysis`
- `save_table`
- `download_data`

### Dashboard-Specific Translations (`{dashboard}/_*_dashboard_core/{lang}_specific.json`)

Platform-specific translations unique to each dashboard:
- Dashboard name and branding
- Platform-specific file input names
- Custom workflow descriptions
- Platform-specific help text

**Example keys for Fermentalg:**
- `page_recipes` → "Recettes Fermentalg"
- `info_csv` → "Fichier Info CSV"
- `raw_data_csv` → "Fichier Raw Data CSV"
- `medium_csv` → "Fichier Medium CSV"
- `follow_up_zip` → "Fichier Follow-up ZIP"

**Example keys for Biolector:**
- `page_recipes` → "Recettes Biolector"
- `biolector_file` → "Fichier Excel Biolector XT"

## 🔨 Building Translations

### Automatic Build

Run the build script to merge common + specific translations:

```bash
cd /lab/user/bricks/gws_plate_reader/src/gws_plate_reader
python3 build_translations.py
```

This generates the complete `fr.json` and `en.json` files in each dashboard's core directory.

### When to Rebuild

Rebuild translations after:
- ✏️ Adding/modifying common translations in `cell_culture_app_core/{lang}.json`
- ✏️ Adding/modifying specific translations in `*_specific.json` files
- ➕ Adding a new dashboard

### Manual Merge Logic

```python
merged_translations = {
    **common_translations,      # Load common first
    **specific_translations     # Override with specific
}
```

If a key exists in both common and specific files, the **specific value takes precedence**.

## 📝 Adding Translations

### Adding Common Translations

1. Edit `cell_culture_app_core/fr.json` and `cell_culture_app_core/en.json`
2. Add your key-value pairs
3. Run `python3 build_translations.py`

**Example:**
```json
{
    "new_analysis_button": "Nouvelle analyse",
    "export_results": "Exporter les résultats"
}
```

### Adding Dashboard-Specific Translations

1. Edit the appropriate `*_specific.json` file:
   - Fermentalg: `fermentalg_dashboard/_fermentalg_dashboard_core/{lang}_specific.json`
   - Biolector: `biolector_dashboard/_biolector_dashboard_core/{lang}_specific.json`
2. Add your key-value pairs
3. Run `python3 build_translations.py`

**Example for Fermentalg:**
```json
{
    "upload_info_csv": "Télécharger le fichier Info CSV",
    "fermentalg_workflow": "Flux de travail Fermentalg"
}
```

## 🆕 Adding a New Dashboard

To add support for a new platform (e.g., Tecan):

1. **Create dashboard structure:**
   ```
   tecan_dashboard/
   └── _tecan_dashboard_core/
       ├── fr_specific.json
       └── en_specific.json
   ```

2. **Create specific translations:**
   ```json
   // fr_specific.json
   {
       "page_recipes": "Recettes Tecan",
       "tecan_file": "Fichier Tecan Excel",
       ...
   }
   ```

3. **Update build script:**
   Edit `build_translations.py` and add to the `dashboards` list:
   ```python
   {
       'name': 'Tecan',
       'path': script_dir / "tecan_dashboard" / "_tecan_dashboard_core"
   }
   ```

4. **Build translations:**
   ```bash
   python3 build_translations.py
   ```

## ⚠️ Important Notes

- **DO NOT manually edit** `{dashboard}/fr.json` or `{dashboard}/en.json` - they are **auto-generated**
- **Always edit** source files:
  - Common: `cell_culture_app_core/{lang}.json`
  - Specific: `{dashboard}/_*_dashboard_core/{lang}_specific.json`
- **Always run** `build_translations.py` after editing source files
- The build script preserves JSON formatting (4-space indentation, UTF-8 encoding)

## 🔍 Finding Where to Add Translations

**Is it used across multiple dashboards?**
- ✅ YES → Add to `cell_culture_app_core/{lang}.json`
- ❌ NO → Add to specific dashboard's `{lang}_specific.json`

**Examples:**

| Translation | Location | Reason |
|------------|----------|--------|
| "Save table" | Common | All dashboards save tables |
| "PCA Analysis" | Common | All dashboards use PCA |
| "Info CSV File" | Fermentalg-specific | Only Fermentalg uses this file type |
| "Biolector XT Excel" | Biolector-specific | Only Biolector uses this format |
| "Quality check" | Common | All dashboards have quality checks |

## 🚀 Quick Reference

```bash
# Edit common translations
vim cell_culture_app_core/fr.json
vim cell_culture_app_core/en.json

# Edit Fermentalg-specific
vim fermentalg_dashboard/_fermentalg_dashboard_core/fr_specific.json
vim fermentalg_dashboard/_fermentalg_dashboard_core/en_specific.json

# Edit Biolector-specific
vim biolector_dashboard/_biolector_dashboard_core/fr_specific.json
vim biolector_dashboard/_biolector_dashboard_core/en_specific.json

# Rebuild all translations
python3 build_translations.py
```

---

**Last Updated:** November 20, 2025  
**Maintained By:** Constellab Development Team
