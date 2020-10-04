from django.urls import path

from . import views

urlpatterns = [
    path('', views.map_page, name='map'),
    path('history', views.history_page, name='history'),
    path('edit', views.edit_page, name='edit'),
    path('login', views.login_page, name='log_in'),
    path('signup', views.sign_up_page, name='sign_up'),
    path('copyright', views.copyright_page, name='copyright'),
    path('help', views.help_page, name='help'),
    path('about', views.about_page, name='about'),
    path('user/<str:username>', views.user_profile, name='user'),
]
