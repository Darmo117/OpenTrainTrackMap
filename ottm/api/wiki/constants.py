ACTION_SHOW = 'show'
ACTION_EDIT = 'edit'
ACTION_SUBMIT = 'submit'
ACTION_HISTORY = 'history'
ACTION_DISCUSS = 'discuss'
ACTION_RAW = 'raw'
ACTIONS: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('ACTION_'))

CT_WIKIPAGE = 'wikipage'
CT_MODULE = 'module'
CT_JS = 'js'
CT_CSS = 'css'
CT_JSON = 'json'
CONTENT_TYPES: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('CT_'))

MIME_TYPES = {
    CT_WIKIPAGE: 'text/plain',
    CT_MODULE: 'text/x-python3',
    CT_JS: 'text/javascript',
    CT_CSS: 'text/css',
    CT_JSON: 'application/json',
}
