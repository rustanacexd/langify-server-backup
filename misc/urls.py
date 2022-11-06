from django.urls import path
from django.views.generic import TemplateView
from frontend_urls import LEGAL_NOTICE, PRIVACY

from . import views

urlpatterns = [
    path('page/stats/', views.StatisticsView.as_view(), name='statistics'),
    path(
        'page/<slug:slug>/<int:index>/',
        views.PageContactView.as_view(),
        name='page_contact',
    ),
    path(LEGAL_NOTICE, TemplateView.as_view(), name='legal_notice'),
    path(PRIVACY, TemplateView.as_view(), name='privacy'),
]
