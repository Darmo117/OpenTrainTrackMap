from django.urls import path

from . import views

urlpatterns = [
    path('', views.map_view, name='map'),
    path('history', views.history, name='history'),
    path('edit', views.edit, name='edit'),
    path('login', views.login, name='login'),
    path('user/<str:username>', views.user_profile, name='user'),
]
