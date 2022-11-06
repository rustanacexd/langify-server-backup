from django.urls import path

from . import views

urlpatterns = [
    path(
        'auth-server/',
        views.AuthServerURL.as_view(),
        name='white-estate_auth_server',
    ),
    path(
        'login/',
        views.CallbackLogin.as_view(),
        name='white-estate_callback_login',
    ),
    path(
        'connect/',
        views.CallbackConnect.as_view(),
        name='white-estate_callback_connect',
    ),
]
