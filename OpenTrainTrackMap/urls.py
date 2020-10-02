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

from main_app import apps

urlpatterns = [
    path('', include(apps.MainAppConfig.name + '.urls')),
    # TODO install WikiPy when available and stable
    # path('wiki', RedirectView.as_view(url='wiki/', permanent=True)),
    # path('wiki/', include('wiki urls.py file')),
    # path('api', RedirectView.as_view(url='api/', permanent=True)),
    # path('api/', include('wiki urls.py file')),
]

handler404 = apps.MainAppConfig.name + '.views.handle404'
handler500 = apps.MainAppConfig.name + '.views.handle500'
