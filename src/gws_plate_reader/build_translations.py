#!/usr/bin/env python3
"""
Build script to merge common and specific translation files for cell culture dashboards.

This script combines:
- Common translations from cell_culture_app_core/{lang}.json
- Dashboard-specific translations from {dashboard}_dashboard/_*_dashboard_core/{lang}_specific.json

The merged translations are written to {dashboard}_dashboard/_*_dashboard_core/{lang}.json
"""

import json
import os
from pathlib import Path


def merge_translations(common_path, specific_path, lang):
    """
    Merge common and specific translations for a given language.

    :param common_path: Path to directory containing common translations
    :param specific_path: Path to directory containing specific translations
    :param lang: Language code (e.g., 'fr', 'en')
    :return: Merged dictionary of translations
    """
    merged = {}

    # Load common translations
    common_file = os.path.join(common_path, f"{lang}.json")
    if os.path.exists(common_file):
        with open(common_file, 'r', encoding='utf-8') as f:
            common_trans = json.load(f)
            merged.update(common_trans)
            print(f"  ✓ Loaded {len(common_trans)} common translations from {common_file}")
    else:
        print(f"  ⚠ Common file not found: {common_file}")

    # Load specific translations (override common if conflicts)
    specific_file = os.path.join(specific_path, f"{lang}_specific.json")
    if os.path.exists(specific_file):
        with open(specific_file, 'r', encoding='utf-8') as f:
            specific_trans = json.load(f)
            merged.update(specific_trans)
            print(f"  ✓ Loaded {len(specific_trans)} specific translations from {specific_file}")
    else:
        print(f"  ⚠ Specific file not found: {specific_file}")

    return merged


def build_dashboard_translations(dashboard_name, dashboard_path, common_path, languages=['fr', 'en']):
    """
    Build merged translation files for a dashboard.

    :param dashboard_name: Name of the dashboard (e.g., 'Fermentalg', 'Biolector')
    :param dashboard_path: Path to dashboard core directory
    :param common_path: Path to common translations directory
    :param languages: List of language codes to process
    """
    print(f"\n📦 Building translations for {dashboard_name} dashboard...")

    for lang in languages:
        print(f"\n  Language: {lang}")
        merged = merge_translations(common_path, dashboard_path, lang)

        # Save merged translations
        output_file = os.path.join(dashboard_path, f"{lang}.json")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=4)

        print(f"  ✅ Wrote {len(merged)} translations to {output_file}")


def main():
    """Main build function."""
    # Get the script directory
    script_dir = Path(__file__).parent.resolve()

    # Define paths
    common_path = script_dir / "cell_culture_app_core"

    dashboards = [
        {
            'name': 'Fermentalg',
            'path': script_dir / "fermentalg_dashboard" / "_fermentalg_dashboard_core"
        },
        {
            'name': 'Biolector',
            'path': script_dir / "biolector_dashboard" / "_biolector_dashboard_core"
        }
    ]

    print("=" * 70)
    print("🌍 Cell Culture Dashboard Translation Builder")
    print("=" * 70)

    # Verify common translations exist
    if not common_path.exists():
        print(f"\n❌ Error: Common translations directory not found: {common_path}")
        return 1

    print(f"\n📂 Common translations directory: {common_path}")

    # Build translations for each dashboard
    for dashboard in dashboards:
        if not dashboard['path'].exists():
            print(f"\n⚠ Warning: Dashboard path not found: {dashboard['path']}")
            continue

        build_dashboard_translations(
            dashboard['name'],
            str(dashboard['path']),
            str(common_path)
        )

    print("\n" + "=" * 70)
    print("✅ Translation build completed successfully!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit(main())
