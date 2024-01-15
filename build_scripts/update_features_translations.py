"""
This script downloads all *.yml localization files for OSM feature types
then generates *.json files to be used by OTTM.
"""
import json
import os.path
import pathlib
import sys

import yaml

import gitdir

# Paths
langs_dir = pathlib.Path('../ottm/settings/langs')
generated_files_dir = langs_dir / 'feature_translations'
raw_files_root = pathlib.Path('osm_translations/raw_files')
locales_path = raw_files_root / 'config/locales'

# Gather available language codes
lang_codes = [os.path.splitext(file.name)[0] for file in langs_dir.glob('*.json')]

# Empty downloads directory
for file in locales_path.iterdir():
    file.unlink()

# Download files
total_files = gitdir.download(
    'https://github.com/openstreetmap/openstreetmap-website/tree/master/config/locales/',
    raw_files_root,
    # Filter out YAML language files that do not have a .json file in OTTM
    lambda file_path: os.path.splitext(file_path.name)[0] in lang_codes
)

# No files? abort without deleting current translation files
if total_files == 0:
    print('No files downloaded, exit')
    sys.exit(1)

if not generated_files_dir.exists():
    generated_files_dir.mkdir(parents=True)
else:
    # Empty output directory
    for file in generated_files_dir.iterdir():
        file.unlink()

# Extract localizations and generate .json files
for file in locales_path.glob('*.yml'):
    with file.open(mode='r', encoding='UTF-8') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(e)
            continue
    code = os.path.splitext(file.name)[0]
    print(f'Generating translations for language code "{code}"')
    values = data[code].get('geocoder', {}).get('search_osm_nominatim', {})
    with (generated_files_dir / f'{code}.json').open(mode='w', encoding='UTF-8') as f:
        json.dump(values, f)
