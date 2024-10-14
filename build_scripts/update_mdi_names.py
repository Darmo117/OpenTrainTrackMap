"""
This scripts generates the file mdi.ts containing the names of all available MDI icon names
and downloads the CSS and font files from MDI’s GitHub repo.
"""
import pathlib
import re

import gitdir


def main():
    mdi_version_pattern = re.compile(r'\$mdi-version:\s*"([\d.]+)"')
    name_pattern = re.compile(r'^\s+(".+"):')

    raw_files_root = pathlib.Path('mdi_names/raw_files')
    scss_file_name = '_variables.scss'
    scss_file = raw_files_root / 'scss' / scss_file_name
    output_ts_file = pathlib.Path('../js-sources/src/map/controls/mdi.ts')
    output_static_dir = pathlib.Path('../ottm/static/ottm/libs/mdi')

    # Download SCSS file
    gitdir.download(
        'https://github.com/Templarian/MaterialDesign-Webfont/tree/master/scss/',
        raw_files_root,
        # Only download the file we are interested in
        lambda file_path: file_path.name == scss_file_name
    )

    def delete_contents(root: pathlib.Path):
        for file in root.glob('*'):
            if file.is_dir():
                delete_contents(file)
                file.rmdir()
            else:
                file.unlink()

    delete_contents(output_static_dir)

    # Download CSS and font files
    gitdir.download(
        'https://github.com/Templarian/MaterialDesign-Webfont/tree/master/',
        output_static_dir,
        # Only download the file we are interested in
        lambda file_path: file_path.parts[0] in ('css', 'fonts')
    )

    names = []
    version = None
    with scss_file.open() as f:
        for line in f.readlines():
            if m := name_pattern.match(line):
                names.append(m.group(1))
            elif m := mdi_version_pattern.match(line):
                version = m.group(1)
    entries = '\n  | '.join(names)

    with output_ts_file.open(mode='w') as f:
        f.write(f"""\
// This file is generated from MDI’s SCSS sources, please do not edit manually!
// MaterialDesign Icons v{version}
type MDIcon =
  | {entries};

export default MDIcon;
""")


if __name__ == '__main__':
    main()
