"""OpenTrainTrackMap URL Configuration."""
from django.urls import path, include
from django.views.generic.base import RedirectView

from wiki import apps as wiki_apps
from ottm import apps

urlpatterns = [
    path('', include(apps.OTTMConfig.name + '.urls')),
    path('wiki', RedirectView.as_view(url='wiki/', permanent=True)),
    path('wiki/', include(wiki_apps.WikiConfig.name + '.urls')),
]

handler404 = apps.OTTMConfig.name + '.views.handle404'
handler500 = apps.OTTMConfig.name + '.views.handle500'
