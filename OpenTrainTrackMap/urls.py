"""OpenTrainTrackMap URL Configuration."""
from django.urls import path, include

from ottm import apps

urlpatterns = [
    path('', include(apps.OTTMConfig.name + '.urls')),
]

handler404 = apps.OTTMConfig.name + '.views.handle404'
handler500 = apps.OTTMConfig.name + '.views.handle500'
