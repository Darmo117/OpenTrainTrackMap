OBJECT_CREATED = 'create'
OBJECT_DELETED = 'delete'
OBJECT_EDIT_ACTIONS: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('OBJECT_'))

RELATION_CREATED = 'create'
RELATION_MODIFIED = 'modify'
RELATION_DELETED = 'delete'
RELATION_EDIT_ACTIONS: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('RELATION_'))

PROPERTY_TYPE = 'type'
PROPERTY_LOCALIZED = 'localized'
PROPERTY_STRING = 'string'
PROPERTY_INT = 'int'
PROPERTY_FLOAT = 'float'
PROPERTY_BOOLEAN = 'boolean'
PROPERTY_UNIT = 'unit'
PROPERTY_DATE_INTERVAL = 'date_interval'
PROPERTY_TYPES: tuple[str, ...] = tuple(v for k, v in globals().items() if k.startswith('PROPERTY_'))
