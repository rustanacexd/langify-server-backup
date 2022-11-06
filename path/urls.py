from django.urls import path

from .api import views

from drf_yasg.utils import swagger_auto_schema
from rest_auth.views import PasswordChangeView, PasswordResetConfirmView


urlpatterns = [
    path('login/', views.LoginUserView.as_view(), name='rest_login'),
    path('logout/', views.LogoutView.as_view(), name='rest_logout'),
    path('registration/', views.RegisterView.as_view(), name='rest_register'),
    path(
        'registration/verify-email/',
        views.ConfirmEmailView.as_view(),
        name='rest_verify_email',
    ),
    path(
        'registration/resend-confirmation/',
        views.ResendConfirmationView.as_view(),
        name='resend_confirmation',
    ),
    path(
        'password/change/',
        swagger_auto_schema(
            method='post',
            operation_id='Password change',
            operation_description='',
            responses={
                200: 'New password has been saved.',
                400: '*Validation errors*',
            },
        )(PasswordChangeView.as_view()),
        name='rest_password_change',
    ),
    path(
        'password/reset/',
        views.TransactionalPasswordResetView.as_view(),
        name='rest_password_reset',
    ),
    path(
        'password/reset/confirm/',
        swagger_auto_schema(
            method='post',
            security=[],
            operation_id='Password reset confirm',
            operation_description='Resets the user\'s password.',
            responses={
                200: 'Password has been reset with the new password.',
                400: '*Validation errors*',
            },
        )(PasswordResetConfirmView.as_view()),
        name='rest_password_reset_confirm',
    ),
    path('user/', views.LittleUserView.as_view(), name='little_user'),
]
