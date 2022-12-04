from ... import util

ACTION_SHOW = 'show'
ACTION_EDIT = 'edit'
ACTION_SUBMIT = 'submit'
ACTION_HISTORY = 'history'
ACTION_DISCUSS = 'discuss'
ACTION_RAW = 'raw'
ACTIONS: tuple[str, ...] = util.gather_globals('^ACTION_', str)

CT_WIKIPAGE = 'wikipage'
CT_MODULE = 'module'
CT_JS = 'js'
CT_CSS = 'css'
CT_JSON = 'json'
CONTENT_TYPES: tuple[str, ...] = util.gather_globals('^CT_', str)

MIME_TYPES = {
    CT_WIKIPAGE: 'text/plain',
    CT_MODULE: 'text/x-python3',
    CT_JS: 'text/javascript',
    CT_CSS: 'text/css',
    CT_JSON: 'application/json',
}
