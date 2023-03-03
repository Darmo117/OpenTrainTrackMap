import dj_database_url

from .settings import *

DEBUG = False

ALLOWED_HOSTS = [
    'opentraintrackmap.herokuapp.com',
]

MIDDLEWARE += ['whitenoise.middleware.WhiteNoiseMiddleware', ]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DATABASES['default'] = dj_database_url.config(default=dj_database_url.config('DATABASE_URL'),
                                              engine='django.db.backends.postgresql_psycopg2')
