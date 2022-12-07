"""This module defines a command that initializes the database."""
import django.core.management.base as dj_mngmt

from ... import models, settings
from ...api import auth
from ...api.groups import *
from ...api.permissions import *
from ...api.wiki import pages, namespaces as w_ns


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
        wiki_user.internal_object.groups.add(models.UserGroup.objects.get(label=GROUP_WIKI_ADMINISTRATOR))
        edit_comment = 'Wiki setup.'

        ns, title = pages.split_title(pages.MAIN_PAGE_TITLE)
        content = f'Welcome to {settings.SITE_NAME}’s wiki!'
        pages.edit_page(None, wiki_user, models.Page(namespace_id=ns.id, title=title), content, edit_comment)

        content = """
/*
 * Put the wiki’s global JavaScript here. It will be loaded on every wiki page, regardless of device.
 */
""".strip()
        pages.edit_page(None, wiki_user, models.Page(namespace_id=w_ns.NS_INTERFACE.id, title='Common.js'), content,
                        edit_comment)
        content = """
/*
 * Put the wiki’s global CSS here. It will be loaded on every wiki page, regardless of device.
 */
""".strip()
        pages.edit_page(None, wiki_user, models.Page(namespace_id=w_ns.NS_INTERFACE.id, title='Common.css'), content,
                        edit_comment)
        content = """
/*
 * Put the wiki’s mobile JavaScript here. It will be loaded on every wiki page on mobile devices only.
 */
""".strip()
        pages.edit_page(None, wiki_user, models.Page(namespace_id=w_ns.NS_INTERFACE.id, title='Mobile.js'), content,
                        edit_comment)
        content = """
/*
 * Put the wiki’s mobile CSS here. It will be loaded on every wiki page on mobile devices only.
 */
""".strip()
        pages.edit_page(None, wiki_user, models.Page(namespace_id=w_ns.NS_INTERFACE.id, title='Mobile.css'), content,
                        edit_comment)

        self.stdout.write('Done.')
