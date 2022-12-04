import django.core.management.base as dj_mngmt

from ... import models
from ...api import auth
from ...api.groups import *
from ...api.permissions import *


class Command(dj_mngmt.BaseCommand):
    help = 'Initializes the database'

    def handle(self, *args, **options):
        self.stdout.write('Initializing DB…')
        self._init_user_groups()
        self._init_ottm_model()
        self._init_default_wiki_pages()
        self.stdout.write('DB initialized successfully.')

    def _init_user_groups(self):
        self.stdout.write('Creating default user groups…')

        models.UserGroup(
            label=GROUP_SUPERUSER,
            permissions=(PERM_EDIT_SCHEMA,),
        ).save()
        models.UserGroup(
            label=GROUP_ADMINISTRATOR,
            permissions=(PERM_EDIT_USER_GROUPS, PERM_BLOCK_USERS),
        ).save()
        models.UserGroup(
            label=GROUP_WIKI_ADMINISTRATOR,
            permissions=(PERM_WIKI_DELETE, PERM_WIKI_RENAME, PERM_WIKI_MASK, PERM_WIKI_EDIT_FILTERS,
                         PERM_WIKI_BLOCK_USERS, PERM_WIKI_EDIT_USER_PAGES),
        ).save()
        models.UserGroup(
            label=GROUP_PATROLLER,
            permissions=(PERM_REVERT,),
        ).save()
        models.UserGroup(
            label=GROUP_WIKI_PATROLLER,
            permissions=(PERM_WIKI_REVERT,),
        ).save()
        models.UserGroup(
            label=GROUP_AUTOPATROLLED,
            permissions=(),  # Empty because it is just a tagging group
        ).save()
        models.UserGroup(
            label=GROUP_WIKI_AUTOPATROLLED,
            permissions=(),  # Empty because it is just a tagging group
        ).save()
        models.UserGroup(
            label=GROUP_USER,
            permissions=(PERM_EDIT_OBJECTS,),
        ).save()
        models.UserGroup(
            label=GROUP_ALL,
            permissions=(PERM_WIKI_EDIT, PERM_WIKI_EDIT),
        ).save()

        self.stdout.write('Done.')

    def _init_ottm_model(self):
        pass  # TODO

    def _init_default_wiki_pages(self):
        self.stdout.write('Initializing wiki default pages…')

        # Create dummy user with throwaway password
        password = models.CustomUser.objects.make_random_password(length=50)
        wiki_user = auth.create_user('Wiki Setup', password=password, ignore_email=True)
        wiki_user.internal_user.groups.add(models.UserGroup.objects.get(label=GROUP_WIKI_ADMINISTRATOR))

        # TODO create pages

        self.stdout.write('Done.')
