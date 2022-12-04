from django.urls import path, include, re_path

from . import views

app_name = 'ottm'
urlpatterns = [
    path('', views.map_page, name='map'),
    path('history', views.history_page, name='history'),
    path('edit', views.edit_page, name='edit'),
    path('log-out', views.logout_page, name='log_out'),
    path('copyright', views.page_handler('copyright'), name='copyright'),
    path('help', views.page_handler('help'), name='help'),
    path('about', views.page_handler('about'), name='about'),
    path('basics', views.page_handler('basics'), name='basics'),
    path('user/', include([
        path('<str:username>/', include([
            path('', views.user_profile, name='user_profile'),
            path('contributions', views.user_contributions, name='user_contributions'),
            path('notes', views.user_notes, name='user_notes'),
        ])),
        path('settings', views.user_settings, name='user_settings'),
    ])),
    path('wiki/', include([
        path('', views.wiki_page, name='wiki_main_page'),
        re_path('(?P<raw_page_title>.*)', views.wiki_page, name='wiki_page'),
    ])),
]
