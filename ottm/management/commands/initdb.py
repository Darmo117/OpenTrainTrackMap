"""This module defines a command that initializes the database."""
import django.db.transaction as dj_db_trans
import django.core.management.base as dj_mngmt

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
        self._init_ottm_model()
        self._init_default_wiki_pages()
        self.stdout.write('DB initialized successfully.')

    def _init_default_languages(self):
        from ... import models
        self.stdout.write('Initializing default languages…')
        dtf1 = models.DateTimeFormat(format='%B, %d %Y %I:%M:%S %p')
        dtf1.save()
        dtf2 = models.DateTimeFormat(format='%d %B %Y %H:%M:%S')
        dtf2.save()
        models.Language(
            code='en',
            name='English',
            writing_direction='ltr',
            default_datetime_format=dtf1,
            available_for_ui=True,
        ).save()
        models.Language(
            code='fr',
            name='Français',
            writing_direction='ltr',
            default_datetime_format=dtf2,
            available_for_ui=True,
        ).save()
        self.stdout.write('Done.')

    def _init_user_groups(self):
        from ... import models
        self.stdout.write('Creating default user groups…')

        models.UserGroup(
            label=GROUP_SUPERUSERS,
            permissions=(PERM_EDIT_SCHEMA,),
        ).save()
        models.UserGroup(
            label=GROUP_GROUPS_MANAGERS,
            permissions=(PERM_EDIT_USER_GROUPS,),
        ).save()
        models.UserGroup(
            label=GROUP_ADMINISTRATORS,
            permissions=(PERM_BLOCK_USERS,),
        ).save()
        models.UserGroup(
            label=GROUP_WIKI_ADMINISTRATORS,
            permissions=(PERM_WIKI_DELETE, PERM_WIKI_RENAME, PERM_WIKI_MASK, PERM_WIKI_EDIT_FILTERS,
                         PERM_WIKI_BLOCK_USERS, PERM_WIKI_EDIT_USER_PAGES, PERM_WIKI_PROTECT, PERM_WIKI_EDIT_INTERFACE),
        ).save()
        models.UserGroup(
            label=GROUP_PATROLLERS,
            permissions=(PERM_REVERT,),
        ).save()
        models.UserGroup(
            label=GROUP_WIKI_PATROLLERS,
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
            label=GROUP_USERS,
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
        from ... import settings, models
        self.stdout.write('Initializing wiki default pages…')

        # Create dummy user with throwaway password
        password = models.CustomUser.objects.make_random_password(length=50)
        wiki_user = auth.create_user('Wiki Setup', password=password, ignore_email=True, is_bot=True)
        wiki_user.internal_object.groups.add(models.UserGroup.objects.get(label=GROUP_WIKI_AUTOPATROLLED))
        wiki_user.internal_object.groups.add(models.UserGroup.objects.get(label=GROUP_WIKI_ADMINISTRATORS))
        edit_comment = 'Wiki setup.'

        content = 'This user is a bot used to setup the wiki.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_USER, wiki_user.username), content, edit_comment)

        ns, title = pages.split_title(pages.MAIN_PAGE_TITLE)
        content = f'Welcome to {settings.SITE_NAME}’s wiki!'
        pages.edit_page(None, wiki_user, pages.get_page(ns, title), content, edit_comment)
        pages.protect_page(wiki_user, pages.get_page(ns, title),
                           models.UserGroup.objects.get(label=GROUP_WIKI_ADMINISTRATORS),
                           reason='Page with high traffic.')
        content = """
/*
 * Put the wiki’s global JavaScript here. It will be loaded on every wiki page, regardless of device.
 */
""".strip()
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Common.js'), content,
                        edit_comment)
        content = """
/*
 * Put the wiki’s global CSS here. It will be loaded on every wiki page, regardless of device.
 */
""".strip()
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Common.css'), content, edit_comment)
        content = """
/*
 * Put the wiki’s mobile JavaScript here. It will be loaded on every wiki page on mobile devices only.
 */
""".strip()
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Mobile.js'), content, edit_comment)
        content = """
/*
 * Put the wiki’s mobile CSS here. It will be loaded on every wiki page on mobile devices only.
 */
""".strip()
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'Mobile.css'), content, edit_comment)
        content = """
* Navigation
** MainPage-url|MainPage-name
** Special:RandomPage|RandomPage-name
* Contribute
** Wiki:Forum|Forum
** Special:RecentChanges|RecentChanges-name
* Help
** Help:Help|HelpPage-name
** Wiki:Templates|Templates-name
** Help:Conventions|Conventions-name
** Help:Download|DownloadData-name
""".strip()
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'SideMenu'), content, edit_comment)
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuNavigation/en'), 'Navigation',
                        edit_comment)
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuNavigation/fr'), 'Navigation',
                        edit_comment)
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuContribute/en'), 'Contribute',
                        edit_comment)
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuContribute/fr'), 'Contribuer',
                        edit_comment)
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuHelp/en'), 'Help', edit_comment)
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'MenuHelp/fr'), 'Aide', edit_comment)
        content = 'You are editing the page.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'EditNotice/en'), content, edit_comment)
        content = 'Vous êtes en train de modifier la page.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'EditNotice/fr'), content, edit_comment)
        content = 'You are creating a new page.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NewPageNotice/en'), content, edit_comment)
        content = 'Vous êtes en train de créer une nouvelle page.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NewPageNotice/fr'), content, edit_comment)
        content = 'This page does not exist.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NoPageNotice/en'), content, edit_comment)
        content = 'Cette page n’existe page.'
        pages.edit_page(None, wiki_user, pages.get_page(w_ns.NS_INTERFACE, 'NoPageNotice/fr'), content, edit_comment)
        # TODO

        self.stdout.write('Done.')
