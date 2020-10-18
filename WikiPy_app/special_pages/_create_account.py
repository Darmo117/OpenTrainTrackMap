import dataclasses
import typing as typ

import django.utils.safestring as dj_safe

from . import SpecialPage, ReturnToPageContext
from .. import page_context


def load_special_page(settings) -> SpecialPage:
    @dataclasses.dataclass(init=False)
    class CreateAccountPageContext(page_context.PageContext):
        create_account_notice: str
        create_account_username: typ.Optional[str]
        create_account_email: typ.Optional[str]
        create_account_invalid_username: bool
        create_account_duplicate_username: bool
        create_account_invalid_password: bool
        create_account_invalid_email: bool

        def __init__(self, context: page_context.PageContext, /, create_account_notice: str,
                     create_account_username: typ.Optional[str], create_account_email: typ.Optional[str],
                     create_account_invalid_username: bool, create_account_duplicate_username: bool,
                     create_account_invalid_password: bool, create_account_invalid_email: bool):
            self._context = context
            self.create_account_notice = create_account_notice
            self.create_account_username = create_account_username
            self.create_account_email = create_account_email
            self.create_account_invalid_username = create_account_invalid_username
            self.create_account_duplicate_username = create_account_duplicate_username
            self.create_account_invalid_password = create_account_invalid_password
            self.create_account_invalid_email = create_account_invalid_email

    class CreateAccountPage(SpecialPage):
        def __init__(self):
            super().__init__(settings, 'create_account', 'Create account')

        def _get_data_impl(self, api, sub_title, base_context, request, **_):
            get_params = request.GET
            return_to = api.get_param(get_params, 'return_to')
            return_to_path = api.get_param(get_params, 'is_path', default=False, expected_type=bool)

            context = ReturnToPageContext(base_context, to=return_to, is_path=return_to_path)

            notice = dj_safe.mark_safe(api.render_wikicode(
                api.get_page_content(4, 'Message-CreateAccountDisclaimer')[0],
                base_context.skin_name,
                disable_comment=True
            ))

            kwargs = {
                'create_account_notice': notice,
                'create_account_username': None,
                'create_account_email': None,
                'create_account_invalid_username': False,
                'create_account_duplicate_username': False,
                'create_account_invalid_password': False,
                'create_account_invalid_email': False,
            }
            if api.get_param(get_params, 'action') == 'create_account':
                context = self.__create_account(api, context, request)
            else:
                context = CreateAccountPageContext(context, **kwargs)

            return context, [], None

        def __create_account(self, api, context, request) -> CreateAccountPageContext:
            post_params = request.POST
            username = api.get_param(post_params, 'wpy-createaccount-username')
            password = api.get_param(post_params, 'wpy-createaccount-password')
            email = api.get_param(post_params, 'wpy-createaccount-email')
            return_to = api.get_param(
                post_params,
                'wpy-createaccount-returnto',
                default=api.as_url_title(api.get_full_page_title(
                    self._settings.MAIN_PAGE_NAMESPACE_ID,
                    self._settings.MAIN_PAGE_TITLE
                ))
            )
            is_path = api.get_param(post_params, 'wpy-createaccount-returntopath', expected_type=bool, default=False)

            kwargs = {
                'create_account_notice': None,
                'create_account_username': username,
                'create_account_email': email,
                'create_account_invalid_username': False,
                'create_account_duplicate_username': False,
                'create_account_invalid_password': False,
                'create_account_invalid_email': False,
            }

            try:
                api.create_user(username, password=password, email=email)
            except api.InvalidUsernameError:
                kwargs['create_account_invalid_username'] = True
            except api.DuplicateUsernameError:
                kwargs['create_account_duplicate_username'] = True
            except api.InvalidPasswordError:
                kwargs['create_account_invalid_password'] = True
            except api.InvalidEmailError:
                kwargs['create_account_invalid_email'] = True
            else:
                context = page_context.RedirectPageContext(context, to=return_to, is_path=is_path)

            return CreateAccountPageContext(context, **kwargs)

    return CreateAccountPage()
