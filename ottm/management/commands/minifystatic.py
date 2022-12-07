"""This module defines a command that manages minified static files."""
import pathlib
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
        nb = self._map('*.min.*', lambda f: f.unlink())
        self.stdout.write(f'{nb} file(s) successfully deleted.')

    def _minify(self):
        self.stdout.write('Minifying static files…')
        nb = self._map('*.js', lambda f: self._minify_(rjsmin.jsmin, 'js', f))
        self.stdout.write(f'Minified {nb} JS file(s).')
        nb = self._map('*.css', lambda f: self._minify_(cssmin.cssmin, 'css', f))
        self.stdout.write(f'Minified {nb} CSS file(s).')

    @staticmethod
    def _minify_(minifier: typ.Callable[[str], str], ext: str, f: pathlib.Path):
        with f.open(encoding='utf8') as fp:
            content = fp.read()
        minified = minifier(content)
        fname = '{0}.min.{1}'.format(f.name.rsplit('.', maxsplit=1)[0], ext)
        with (f.parent / fname).open(mode='w', encoding='utf8') as fp:
            fp.write(minified)

    @staticmethod
    def _map(pattern: str, callback: typ.Callable[[pathlib.Path], None]) -> int:
        nb = 0
        for file in map(pathlib.Path, (settings.BASE_DIR / 'ottm/static').rglob(pattern)):
            if 'libs' not in file.parts and '.min.' not in file.name and file.is_file():
                callback(file)
                nb += 1
        return nb
