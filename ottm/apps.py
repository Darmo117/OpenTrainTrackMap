from django.apps import AppConfig
import django.db.utils as _dj_utils


class OTTMConfig(AppConfig):
    name = 'ottm'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import settings
        try:
            # Run only now as the database needs to be initialized first
            settings.init_languages()
        except _dj_utils.OperationalError:
            pass
