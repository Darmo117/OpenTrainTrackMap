from django.apps import AppConfig
import django.db.utils as _dj_utils


class OTTMConfig(AppConfig):
    name = 'ottm'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import settings
        from .api import bg_tasks
        try:
            # Run only now as the database needs to be initialized first
            settings.init_languages()
        except _dj_utils.OperationalError:
            pass
        bg_tasks.start()
