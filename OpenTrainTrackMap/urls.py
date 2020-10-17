"""OpenTrainTrackMap URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, include
from django.views.generic.base import RedirectView

from WikiPy_app import apps as wiki_apps
from main_app import apps

urlpatterns = [
    path('', include(apps.MainAppConfig.name + '.urls')),
    path('wiki', RedirectView.as_view(url='wiki/', permanent=True)),
    path('wiki/', include(wiki_apps.WikiPyAppConfig.name + '.urls')),
    path('wiki-api', RedirectView.as_view(url='wiki-api/', permanent=True)),
    path('wiki-api/', include(wiki_apps.WikiPyAppConfig.name + '.urls_api')),
]

handler404 = apps.MainAppConfig.name + '.views.handle404'
handler500 = apps.MainAppConfig.name + '.views.handle500'
