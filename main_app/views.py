from . import context
from . import settings


def map_view(request):
    return None


def history(request):
    return None


def edit(request):
    return None


def login(request):
    return None


def user_profile(request):
    return None


def handle404(request, exception):
    pass


def handle500(request):
    pass


def _get_base_context(no_index: bool):
    return context.PageContext(
        site_name=settings.SITE_NAME,
        noindex=no_index,
        user=None
    )
