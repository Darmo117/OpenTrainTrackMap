"""This module defines a command that manages minified static files."""
import pathlib
import re
import typing as typ

import cssmin
import django.core.management.base as dj_mngmt
import rjsmin
from django.conf import settings


class Command(dj_mngmt.BaseCommand):
    help = 'Minifies all JS and CSS static files (except those in libs/)'

    def add_arguments(self, parser: dj_mngmt.CommandParser):
        parser.add_argument(
            '-p', '--purge',
            action='store_true',
            dest='purge',
            help='Purge all minified static files (except those in libs/).',
        )

    def handle(self, *args: str, **options):
        if options.get('purge'):
            self._purge()
        else:
            self._minify()

    def _purge(self):
        self.stdout.write('Purging minified static files…')
        nb = self._apply('*.min.*', lambda f: f.unlink())
        self.stdout.write(f'{nb} file(s) successfully deleted.')

    def _minify(self):
        self.stdout.write('Minifying static files…')
        nb = self._apply('*.js', lambda f: self._minify_code(rjsmin.jsmin, f))
        self.stdout.write(f'Minified {nb} JS file(s).')
        nb = self._apply('*.css', lambda f: self._minify_code(cssmin.cssmin, f))
        self.stdout.write(f'Minified {nb} CSS file(s).')

    def _minify_code(self, minifier: typ.Callable[[str], str], f: pathlib.Path):
        with f.open(encoding='utf-8') as fp:
            content = fp.read()
        minified = minifier(self._adapt_imports(content))
        fname = '{0}.min.{1}'.format(*f.name.rsplit('.', maxsplit=1))
        with (f.parent / fname).open(mode='w', encoding='utf-8') as fp:
            fp.write(minified)

    def _adapt_imports(self, content: str) -> str:
        """Add ".min" to all imports that are not from the ottm/libs/ directory.

        :param content: Source code to modify.
        :return: The modified source code.
        """

        def repl(m: re.Match[str]) -> str:
            import_, path = m.groups()
            if '/libs/' not in path:
                path = path.replace('.js', '.min.js')
            return f'import {import_} from "{path}";'

        return re.sub('import (.+) from "([^"]+)";', repl, content)

    def _apply(self, pattern: str, callback: typ.Callable[[pathlib.Path], None]) -> int:
        dirs = []
        with (settings.BASE_DIR / 'minify.txt').open(encoding='utf-8') as f:
            for line in f:
                dirs.append(settings.BASE_DIR / line.strip())
        nb = 0
        for directory in dirs:
            for file in map(pathlib.Path, directory.rglob(pattern)):
                if 'libs' not in file.parts and self._test_file_name(file.name) and file.is_file():
                    callback(file)
                    nb += 1
        return nb

    def _test_file_name(self, fname: str) -> bool:
        return '.min.' not in fname and 'bundle-' not in fname
