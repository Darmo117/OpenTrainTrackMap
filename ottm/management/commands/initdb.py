"""This module defines a command that initializes the database."""
import secrets

import django.core.management.base as dj_mngmt
import django.db.transaction as dj_db_trans

from ...api import auth
from ...api.groups import *
from ...api.permissions import *
from ...api.wiki import namespaces as w_ns, pages


class Command(dj_mngmt.BaseCommand):
    help = 'Initializes the database'

    @dj_db_trans.atomic
    def handle(self, *args, **options):
        self.stdout.write('Initializing DB…')
        self._init_default_languages()
        self._init_user_groups()
        self._create_superuser()
        self._init_ottm_model()
        self._init_default_wiki_pages()
        self.stdout.write('DB initialized successfully.')

    def _init_default_languages(self):
        from ... import data_model
        self.stdout.write('Initializing default languages…')
        dtf1 = data_model.DateTimeFormat(format='%B, %d %Y %I:%M:%S %p')
        dtf1.save()
        dtf2 = data_model.DateTimeFormat(format='%d %B %Y %H:%M:%S')
        dtf2.save()
        dtf3 = data_model.DateTimeFormat(format='%B, %d%s %Y %I:%M:%S %p')
        dtf3.save()
        dtf4 = data_model.DateTimeFormat(format='%d%s %B %Y %H:%M:%S')
        dtf4.save()
        data_model.Language(
            code='en',
            name='English',
            writing_direction='ltr',
            default_datetime_format=dtf1,
            available_for_ui=True,
        ).save()
        data_model.Language(
            code='fr',
            name='Français',
            writing_direction='ltr',
            default_datetime_format=dtf2,
            available_for_ui=True,
        ).save()
        data_model.Language(
            code='eo',
            name='Esperanto',
            writing_direction='ltr',
            default_datetime_format=dtf4,
            available_for_ui=True,
        ).save()
        self.stdout.write('Done.')

    def _init_user_groups(self):
        from ... import data_model
        self.stdout.write('Creating default user groups…')

        data_model.UserGroup(
            label=GROUP_SUPERUSERS,
            permissions=(PERM_EDIT_SCHEMA,),
        ).save()
        data_model.UserGroup(
            label=GROUP_GROUPS_MANAGERS,
            permissions=(PERM_EDIT_USER_GROUPS,),
        ).save()
        data_model.UserGroup(
            label=GROUP_ADMINISTRATORS,
            permissions=(PERM_BLOCK_USERS, PERM_RENAME_USERS, PERM_MASK,),
        ).save()
        data_model.UserGroup(
            label=GROUP_WIKI_ADMINISTRATORS,
            permissions=(PERM_WIKI_DELETE, PERM_WIKI_EDIT_FILTERS, PERM_WIKI_EDIT_USER_PAGES, PERM_WIKI_PROTECT,
                         PERM_WIKI_EDIT_INTERFACE,),
        ).save()
        data_model.UserGroup(
            label=GROUP_PATROLLERS,
            permissions=(PERM_REVERT,),
        ).save()
        data_model.UserGroup(
            label=GROUP_WIKI_PATROLLERS,
            permissions=(PERM_WIKI_REVERT,),
        ).save()
        data_model.UserGroup(
            label=GROUP_AUTOPATROLLED,
            permissions=(),  # Empty because it is just a tagging group
        ).save()
        data_model.UserGroup(
            label=GROUP_WIKI_AUTOPATROLLED,
            permissions=(),  # Empty because it is just a tagging group
        ).save()
        data_model.UserGroup(
            label=GROUP_USERS,
            assignable_by_users=False,
            permissions=(PERM_EDIT_OBJECTS, PERM_WIKI_RENAME,),
        ).save()
        data_model.UserGroup(
            label=GROUP_ALL,
            assignable_by_users=False,
            permissions=(PERM_WIKI_EDIT,),
        ).save()

        self.stdout.write('Done.')

    def _create_superuser(self):
        self.stdout.write('Creating superuser…')

        password = self._generate_password()
        self.stdout.write(f'Generated temporary password: {password}')
        superuser = auth.create_user('Admin', password=password, ignore_email=True)
        auth.add_user_to_groups(superuser, *GROUPS)

        self.stdout.write('Done.')

    @staticmethod
    def _generate_password():
        return secrets.token_hex()

    def _init_ottm_model(self):
        pass  # TODO

    def _init_default_wiki_pages(self):
        from ... import settings, data_model
        self.stdout.write('Initializing wiki default pages…')

        # Create dummy user with throwaway password
        password = self._generate_password()
        wiki_user = auth.create_user(settings.WIKI_SETUP_USERNAME, password=password, ignore_email=True, is_bot=True)
        auth.add_user_to_groups(wiki_user, GROUP_WIKI_AUTOPATROLLED, GROUP_WIKI_ADMINISTRATORS)
        edit_comment = 'Wiki setup.'

        content = 'This user is a bot used to setup the wiki.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_USER, wiki_user.username), content, edit_comment)

        ns, title = pages.split_title(pages.MAIN_PAGE_TITLE)
        content = f'Welcome to {settings.SITE_NAME}’s wiki!'
        pages.edit_page(wiki_user, pages.get_page(ns, title), content, edit_comment)
        pages.protect_page(wiki_user, pages.get_page(ns, title),
                           data_model.UserGroup.objects.get(label=GROUP_WIKI_ADMINISTRATORS),
                           protect_talks=False,
                           reason='Page with high traffic.')
        # language=JS
        content = """
/*
 * Put the wiki’s global JavaScript here. It will be loaded on every wiki page, regardless of device.
 */
""".strip()
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Common.js'), content, edit_comment)
        # language=CSS
        content = """
/*
 * Put the wiki’s global CSS here. It will be loaded on every wiki page, regardless of device.
 */
""".strip()
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Common.css'), content, edit_comment)
        # language=JS
        content = """
/*
 * Put the wiki’s mobile JavaScript here. It will be loaded on every wiki page on mobile devices only.
 */
""".strip()
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Mobile.js'), content, edit_comment)
        # language=CSS
        content = """
/*
 * Put the wiki’s mobile CSS here. It will be loaded on every wiki page on mobile devices only.
 */
""".strip()
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Mobile.css'), content, edit_comment)
        content = """
* Navigation
** MainPage-url|MainPage-name
** Special:RandomPage|RandomPage-name
* Contribute
** Special:Forum|Forum-name
** Special:RecentChanges|RecentChanges-name
* Help
** Help:Help|HelpPage-name
** Wiki:Templates|Templates-name
** Help:Conventions|Conventions-name
** Help:Download|DownloadData-name
""".strip()
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'SideMenu'), content, edit_comment)
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuNavigation/en'), 'Navigation', edit_comment)
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuNavigation/fr'), 'Navigation', edit_comment)
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuContribute/en'), 'Contribute', edit_comment)
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuContribute/fr'), 'Contribuer', edit_comment)
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuHelp/en'), 'Help', edit_comment)
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuHelp/fr'), 'Aide', edit_comment)
        content = 'You are editing the page.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'EditNotice/en'), content, edit_comment)
        content = 'Vous êtes en train de modifier la page.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'EditNotice/fr'), content, edit_comment)
        content = 'You are creating a new page.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NewPageNotice/en'), content, edit_comment)
        content = 'Vous êtes en train de créer une nouvelle page.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NewPageNotice/fr'), content, edit_comment)
        content = 'This page does not exist.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NoPageNotice/en'), content, edit_comment)
        content = 'Cette page n’existe page.'
        pages.edit_page(wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NoPageNotice/fr'), content, edit_comment)
        # TODO

        self.stdout.write('Done.')
