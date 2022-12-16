import enum


class NotificationEmailFrequency(enum.Enum):
    NONE = 'none'
    IMMEDIATELY = 'immediately'
    DAILY = 'daily'
    WEEKLY = 'weekly'
