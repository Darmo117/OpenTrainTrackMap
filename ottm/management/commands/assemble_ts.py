"""This module defines a command that injects all the index-inject-*.ts files
before the TypeScript modules are compiled by webpack."""
import pathlib
import re

import django.core.management.base as dj_mngmt


class Command(dj_mngmt.BaseCommand):
    help = 'Injects all the index-inject-*.ts files before the TypeScript modules are compiled by webpack'

    PATH = pathlib.Path('js', 'modules')

    def add_arguments(self, parser: dj_mngmt.CommandParser):
        parser.add_argument(
            '-p', '--purge',
            action='store_true',
            dest='purge',
            help='Purge all generated index-*.ts files.',
        )

    def handle(self, *args: str, **options):
        if options.get('purge'):
            self.stdout.write('Purging generated files…')
            for file in self.PATH.glob('index-*.ts'):
                file.unlink()
        else:
            self.stdout.write('Injecting code…')
            for file in self.PATH.glob('inject-*.ts'):
                self._inject_file(file)
        self.stdout.write('Done.')

    def _inject_file(self, file: pathlib.Path):
        self.stdout.write(f'Injecting {file.name}…')
        imports = []
        inits = []
        parsing_imports = False
        parsing_inits = False
        with file.open() as in_f:
            for line in in_f.readlines():
                if re.fullmatch(r'// begin imports\n', line):
                    if parsing_inits:
                        raise RuntimeError('missing section end: init')
                    parsing_imports = True
                elif re.fullmatch(r'// *end imports\n?', line):
                    parsing_imports = False
                elif re.fullmatch(r'// *begin init\n', line):
                    if parsing_imports:
                        raise RuntimeError('missing section end: imports')
                    parsing_inits = True
                elif re.fullmatch(r'// *end init\n?', line):
                    parsing_inits = False
                elif parsing_imports:
                    imports.append(line)
                elif parsing_inits:
                    inits.append(line)

        subname = re.fullmatch(r'inject-(\w+)\.ts', file.name).group(1)
        with (self.PATH / 'index.ts').open() as template_f:
            output = template_f.read() \
                .replace('// `<IMPORTS_PLACEHOLDER>`', ''.join(imports).strip()) \
                .replace('// `<INIT_PLACEHOLDER>`', ''.join(inits).strip())
            fname = f'index-{subname}.ts'
            with (self.PATH / fname).open(mode='w') as out_f:
                out_f.write(output)
                self.stdout.write(f'Result generated in {fname}')
