"""This module defines constants used by the wiki."""
ACTION_READ = 'read'
ACTION_EDIT = 'edit'
ACTION_SUBMIT = 'submit'
ACTION_HISTORY = 'history'
ACTION_TALK = 'talk'
ACTION_INFO = 'info'
ACTION_RAW = 'raw'
ACTIONS: dict[str, str] = {k: v for k, v in globals().items() if k.startswith('ACTION_')}

CT_WIKIPAGE = 'wikipage'
CT_MODULE = 'module'
CT_JS = 'js'
CT_CSS = 'css'
CT_JSON = 'json'
CONTENT_TYPES: dict[str, str] = {k: v for k, v in globals().items() if k.startswith('CT_')}

MIME_TYPES = {
    CT_WIKIPAGE: 'text/plain',
    CT_MODULE: 'text/x-python3',
    CT_JS: 'text/javascript',
    CT_CSS: 'text/css',
    CT_JSON: 'application/json',
}

LANGUAGE_CODES = {
    CT_WIKIPAGE: 'wikicode',
    CT_MODULE: 'python',
    CT_JS: 'js',
    CT_CSS: 'css',
    CT_JSON: 'json',
}

FILE_PREVIEW_SIZES = ((320, 600), (640, 480), (800, 600), (1024, 768), (1280, 1024), (2560, 2048))
