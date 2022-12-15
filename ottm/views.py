"""This module defines all page view handlers."""
import typing as typ

import django.core.handlers.wsgi as dj_wsgi
import django.http.response as dj_response
import django.shortcuts as dj_scut
import requests

from . import forms, page_context, requests, view_handlers as _vh
from .api import auth, errors
from .api.wiki import constants as w_cons, namespaces as w_ns, pages as w_pages, special_pages as w_sp


def get_tile(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """API view that handles map tile querying.

    Expected GET parameters:
        - provider (str): Name of the tile provider.
        - x (int): Tile’s x position.
        - y (int): Tile’s y position.
        - z (int): Zoom value.
    """
    try:
        x = int(request.GET.get('x'))
        y = int(request.GET.get('y'))
        z = int(request.GET.get('z'))
    except ValueError:
        return dj_response.HttpResponseBadRequest()
    provider = request.GET.get('provider')
    if provider == 'maptiler':
        url = f'https://api.maptiler.com/tiles/satellite/{z}/{x}/{y}.jpg?key=5PelNcEc4zGc3OEutmIG'
        response = requests.get(url)
        # Remove Connection header as it may cause issues with Django
        del response.headers['Connection']
        return dj_response.HttpResponse(response.content, status=response.status_code, headers=response.headers)
    return dj_response.HttpResponseNotFound(f'invalid provider {provider}')


def map_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """OTTM map page handler."""
    request_params = requests.RequestParams(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _vh.get_map_page_context(request_params)
    })


# TODO redirect to login page with alert-warning if user not logged in
def edit_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """OTTM map editing page handler."""
    request_params = requests.RequestParams(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _vh.get_map_page_context(request_params, action=_vh.EDIT_MAP, no_index=True)
    })


def history_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """OTTM map history page handler."""
    request_params = requests.RequestParams(request)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _vh.get_map_page_context(request_params, action=_vh.MAP_HISTORY, no_index=True)
    })


def page_handler(page_name: str) -> typ.Callable[[dj_wsgi.WSGIRequest], dj_response.HttpResponse]:
    """Generate a page view handler for the given page name.

    :param page_name: Page’s name.
    :return: The view function.
    """

    def handler(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
        request_params = requests.RequestParams(request)
        return dj_scut.render(request, f'ottm/{page_name}.html', context={
            'context': _vh.get_page_context(request_params, page_name)
        })

    return handler


def signup_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """Sign-up page handler."""
    request_params = requests.RequestParams(request)
    if not request_params.user.is_authenticated:
        if request_params.post:
            form = forms.SignUpForm(post=request_params.post)
            if form.is_valid():
                # All errors should have been handled by the form already
                user = auth.create_user(
                    form.cleaned_data['username'],
                    form.cleaned_data['email'],
                    form.cleaned_data['password'],
                )
                if user:
                    auth.log_in(request, form.cleaned_data['username'], form.cleaned_data['password'])
                    return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:help'))
        else:
            form = forms.SignUpForm()
    else:
        form = None
    return dj_scut.render(request, 'ottm/sign-up.html', context={
        'context': _vh.get_sign_up_page_context(request_params, form)
    })


def login_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """Login page handler."""
    request_params = requests.RequestParams(request)
    global_errors = []
    if not request_params.user.is_authenticated:
        if request_params.post:
            form = forms.LoginForm(post=request_params.post)
            if form.is_valid():
                # All errors should have been handled by the form already
                if auth.log_in(request, form.cleaned_data['username'], form.cleaned_data['password']):
                    return dj_response.HttpResponseRedirect(request_params.return_to)
                global_errors.append('invalid_credentials')
        else:
            form = forms.LoginForm()
    else:
        form = None
    return dj_scut.render(request, 'ottm/login.html', context={
        'context': _vh.get_login_page_context(request_params, form, global_errors)
    })


def logout_page(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """Logout page handler."""
    request_params = requests.RequestParams(request)
    if auth.get_user_from_request(request).is_authenticated:
        auth.log_out(request)
    return dj_response.HttpResponseRedirect(request_params.return_to)


def user_profile(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    """User profile page handler."""
    request_params = requests.RequestParams(request)
    target_user = auth.get_user_from_name(username)
    return dj_scut.render(request, 'ottm/user-profile.html', context={
        'context': _vh.get_user_page_context(request_params, target_user)
    })


def user_settings(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """User settings page handler."""
    request_params = requests.RequestParams(request)

    if not request_params.user.is_authenticated:
        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:map'))

    return dj_scut.render(request, 'ottm/user-settings.html', context={
        'context': _vh.get_page_context(request_params, 'user_settings')
    })


def user_contributions(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    """User OTTM contributions page handler."""
    request_params = requests.RequestParams(request)
    target_user = auth.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/map.html', context={
        'context': _vh.get_map_page_context(request_params, action=_vh.MAP_HISTORY)
    })


def user_notes(request: dj_wsgi.WSGIRequest, username: str) -> dj_response.HttpResponse:
    """User notes page handler."""
    request_params = requests.RequestParams(request)
    target_user = auth.get_user_from_name(username)

    return dj_scut.render(request, 'ottm/user-notes.html', context={
        'context': _vh.get_page_context(request_params, 'notes', no_index=True)
    })


def wiki_page(request: dj_wsgi.WSGIRequest, raw_page_title: str = '') -> dj_response.HttpResponse:
    """Wiki page handler.

    :param request: Client request.
    :param raw_page_title: Page title extracted from the URL.
    """
    if not raw_page_title:
        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': w_pages.MAIN_PAGE_TITLE
        }))
    if raw_page_title.endswith('/'):  # Remove trailing '/'
        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
            'raw_page_title': raw_page_title[:-1]
        }))
    request_params = requests.RequestParams(request)
    page_title = w_pages.get_correct_title(raw_page_title)
    ns, title = w_pages.split_title(page_title)
    page = w_pages.get_page(ns, title)
    js_config = w_pages.get_js_config(page, request_params.wiki_action)

    if ns == w_ns.NS_SPECIAL:
        special_page = w_sp.SPECIAL_PAGES.get(page.base_name)
        if special_page is None:
            context = page_context.WikiSpecialPageContext(
                request_params,
                page=page,
                page_exists=False,
                js_config=js_config,
            )
            status = 404
        elif not special_page.can_user_access(request_params.user):
            context = page_context.WikiSpecialPageContext(
                request_params,
                page=page,
                page_exists=True,
                js_config=js_config,
                required_perms=special_page.permissions_required,
            )
            status = 403
        else:
            data = special_page.process_request(request_params, title)
            if isinstance(data, w_sp.Redirect):
                return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
                    'raw_page_title': w_pages.url_encode_page_title(data.page_title),
                }))
            context = page_context.WikiSpecialPageContext(
                request_params,
                page=page,
                page_exists=True,
                js_config=js_config,
                required_perms=special_page.permissions_required,
                kwargs=data,
            )
            status = 200

    else:
        revid: str | None = request_params.get.get('revid')
        if revid and revid.isascii() and revid.isnumeric():
            revision_id = int(revid)
        else:
            revision_id = None

        match request_params.wiki_action:
            case w_cons.ACTION_RAW:
                return dj_response.HttpResponse(
                    content=page.get_content(),
                    content_type=w_cons.MIME_TYPES[page.content_type],
                    status=200 if page.exists else 404,
                )
            case w_cons.ACTION_EDIT:
                context = _vh.wiki_page_edit_context(request_params, page, revision_id, js_config)
            case w_cons.ACTION_SUBMIT:
                form = forms.WikiEditPageForm(post=request.POST)
                if not form.is_valid():
                    context = _vh.wiki_page_edit_context(request_params, page, revision_id, js_config, form=form)
                else:
                    try:
                        w_pages.edit_page(
                            request,
                            request_params.user,
                            page,
                            form.cleaned_data['content'],
                            form.cleaned_data['comment'],
                            form.cleaned_data['minor_edit'],
                            form.cleaned_data['follow_page'],
                            form.cleaned_data['hidden_category'],
                            form.cleaned_data['section_id']
                        )
                    except errors.MissingPermissionError:
                        context = _vh.wiki_page_edit_context(request_params, page, revision_id, js_config)
                    except errors.ConcurrentWikiEditError:
                        # TODO form containing concurrent page content
                        context = _vh.wiki_page_edit_context(request_params, page, revision_id, js_config,
                                                             concurrent_edit_error=True)
                    else:
                        # Redirect to normal view
                        return dj_response.HttpResponseRedirect(dj_scut.reverse('ottm:wiki_page', kwargs={
                            'raw_page_title': page.full_title,
                        }))
            case w_cons.ACTION_HISTORY:
                context = _vh.wiki_page_history_context(request_params, page, js_config)
            case w_cons.ACTION_TALK:
                context = _vh.wiki_page_talk_context(request_params, page, js_config)
            case w_cons.ACTION_INFO:
                context = _vh.wiki_page_info_context(request_params, page, js_config)
            case _:
                context = _vh.wiki_page_read_context(request_params, page, revision_id, js_config)
        status = 200 if context.page.exists else 404

    ctxt = {
        'context': context,
        **w_cons.__dict__,
        **w_ns.NAMESPACES_DICT,
    }
    return dj_scut.render(request, 'ottm/wiki/page.html', context=ctxt, status=status)


def handle404(request: dj_wsgi.WSGIRequest, _) -> dj_response.HttpResponse:
    """404 error page handler."""
    pass  # TODO 404


def handle500(request: dj_wsgi.WSGIRequest) -> dj_response.HttpResponse:
    """500 error page handler."""
    pass  # TODO 500
