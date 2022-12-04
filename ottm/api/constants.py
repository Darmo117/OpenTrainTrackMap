from .. import util

OBJECT_CREATED = 'create'
OBJECT_DELETED = 'delete'
OBJECT_EDIT_ACTIONS = util.gather_globals('^OBJECT_', str)

RELATION_CREATED = 'create'
RELATION_MODIFIED = 'modify'
RELATION_DELETED = 'delete'
RELATION_EDIT_ACTIONS = util.gather_globals('^RELATION_', str)

PROPERTY_TYPE = 'type'
PROPERTY_LOCALIZED = 'localized'
PROPERTY_STRING = 'string'
PROPERTY_INT = 'int'
PROPERTY_FLOAT = 'float'
PROPERTY_BOOLEAN = 'boolean'
PROPERTY_UNIT = 'unit'
PROPERTY_DATE_INTERVAL = 'date_interval'
PROPERTY_TYPES = util.gather_globals('^PROPERTY_', str)
