"""langify URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/dev/topics/http/urls/
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
from inspect import cleandoc

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from drf_yasg.views import get_schema_view
from rest_auth.registration.views import (
    SocialAccountDisconnectView,
    SocialAccountListView,
)
from rest_framework.documentation import include_docs_urls
from rest_framework_extensions.routers import ExtendedDefaultRouter

import frontend_urls
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib.staticfiles.views import serve as serve_static
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from misc.api import (
    DeveloperCommentViewSet,
    E2ETestsViewSet,
    LanguageNewsletterView,
    PageViewSet,
)
from misc.views import ConfirmEmailRedirect, home_view
from panta.api import views as panta_views
from path.api import views as path_views
from style_guide.api import views as style_guide_views
from white_estate.views import EqualSentencesView

router = ExtendedDefaultRouter()
# Private
router.register(r'trustees', panta_views.TrusteeViewSet, basename='trustee')
router.register(r'authors', panta_views.AuthorViewSet, basename='author')
router.register(r'licences', panta_views.LicenceViewSet, basename='licence')
router.register(
    r'references', panta_views.ReferenceViewSet, basename='reference'
)
router.register(r'pages', PageViewSet, basename='page')
router.register(
    r'comments', DeveloperCommentViewSet, basename='developercomment'
)
router.register(
    r'user/email-addresses',
    path_views.EmailAddressViewSet,
    basename='emailaddress',
)
router.register(
    r'user/last-activities',
    panta_views.LastActivitiesViewSet,
    basename='lastactivities',
)
if settings.DEBUG:
    router.register(r'test', E2ETestsViewSet, basename='e2e_test')
(
    router.register(
        r'originals', panta_views.OriginalWorkViewSet, basename='originalwork'
    ).register(
        r'segments',
        panta_views.OriginalSegmentViewSet,
        basename='originalsegment',
        parents_query_lookups=['work'],
    )
)

translation_router = router.register(
    r'translations',
    panta_views.TranslatedWorkViewSet,
    basename='translatedwork',
)
translated_segment_router = translation_router.register(
    r'segments',
    panta_views.TranslatedSegmentViewSet,
    basename='translatedsegment',
    parents_query_lookups=['work'],
)
translated_segment_router.register(
    r'timeline',
    panta_views.TimelineView,
    basename='timeline',
    parents_query_lookups=['work', 'position'],
)
translated_segment_router.register(
    r'history',
    panta_views.TranslatedSegmentHistoryViewSet,
    basename='historicaltranslatedsegment',
    parents_query_lookups=['work', 'position'],
)
translated_segment_router.register(
    r'drafts',
    panta_views.SegmentDraftHistoryViewSet,
    basename='historicalsegmentdraft',
    parents_query_lookups=['work', 'position'],
)
translated_segment_router.register(
    r'comments',
    panta_views.SegmentCommentViewSet,
    basename='segmentcomment',
    parents_query_lookups=['work', 'position'],
)

style_guide_router = router.register(
    r'styleguide', style_guide_views.StyleGuideView, basename='styleguide'
)
style_guide_router.register(
    r'issues',
    style_guide_views.IssueViewSet,
    basename='issues',
    parents_query_lookups=['style_guide__language'],
)
issue_router = style_guide_router.register(
    r'issues',
    style_guide_views.IssueViewSet,
    basename='issues',
    parents_query_lookups=['style_guide__language'],
)

issue_router.register(
    r'comments',
    style_guide_views.IssueCommentViewSet,
    basename='issuecomment',
    parents_query_lookups=['issue__style_guide__language', 'issue'],
)

issue_router.register(
    r'reactions',
    style_guide_views.IssueReactionViewSet,
    basename='issuereaction',
    parents_query_lookups=['issue__style_guide__language', 'issue'],
)


# Public TODO


api_urlpatterns = [
    path(
        'api/translations/filters/',
        panta_views.TranslatedWorkFiltersView.as_view(),
        name='work_filters',
    ),
    path('api/', include(router.urls)),
    path(
        'api/segments/<str:language>/<str:reference>/',
        panta_views.TranslatedSegmentByReferenceView.as_view(),
        name='segment_by_reference',
    ),
    path('api/user/', path_views.OwnUserView.as_view(), name='user'),
    path(
        'api/user/personal-data/',
        path_views.PersonalDataView.as_view(),
        name='personal_data',
    ),
    path(
        'api/user/export-data/',
        path_views.ExportPersonalDataView.as_view(),
        name='export_personal_data',
    ),
    path(
        'api/users/<str:username>/',
        path_views.CommunityUserProfileView.as_view(),
        name='community_user_profile',
    ),
    path(
        'api/users/<str:public_id>/flag/',
        path_views.FlagUserAPIView.as_view(),
        name='flag_user',
    ),
    path('api/auth/', include('path.urls')),
    path('api/auth/social/white-estate/', include('white_estate.urls')),
    path(
        'api/auth/user/social-accounts/',
        swagger_auto_schema(
            method='get',
            operation_id='Social accounts',
            operation_description=(
                'Lists the social accounts of the currently logged in user.'
            ),
        )(SocialAccountListView.as_view()),
        name='social_account_list',
    ),
    path(
        'api/auth/user/social-accounts/<int:pk>/disconnect/',
        swagger_auto_schema(
            method='post',
            operation_id='Social account disconnect',
            operation_description=(
                'Disconnects a social account from the remote service.'
            ),
            responses={200: '*unknown*', 400: '*Validation errors*'},
        )(SocialAccountDisconnectView.as_view()),
        name='social_account_disconnect',
    ),
    path(
        'api/languages/', panta_views.LanguageView.as_view(), name='languages'
    ),
    path(
        'api/newsletters/languages/',
        LanguageNewsletterView.as_view(),
        name='newsletter_languages',
    ),
    path('api/health/', include('health_check.urls')),
]

api_description = cleandoc(
    """
    The private API for use between front- and backend

    **Note:** You have to be authenticated and need some reputation in
    German to see all endpoints!

    You can also use the [Swagger UI](swagger/) if you prefer it.

    ### A note about errors with status code 400

    These errors are not documented here if the UI displays a form
    or something similar.

    The response objects may contain following content:

    * Field errors where the response object exists of key-value
    pairs with the field name as key and a list of error messages
    as value.
    * Non field errors which are not assigned to a specific field
    with the key `nonFieldErrors` and a list of error messages as
    value.
    """
)

schema_view = get_schema_view(
    openapi.Info(
        title='Ellen4all API', default_version='v4', description=api_description
    )
)


urlpatterns = api_urlpatterns + [
    path('admin/', admin.site.urls),
    path('page/sentences/', EqualSentencesView.as_view(), name='sentences'),
    path('', include('misc.urls')),
    path(
        'api/docs/',
        staff_member_required()(schema_view.with_ui('redoc', cache_timeout=0)),
        name='schema_redoc',
    ),
    path(
        'api/docs/swagger/',
        staff_member_required()(
            schema_view.with_ui('swagger', cache_timeout=0)
        ),
        name='schema_swagger_ui',
    ),
    # Frontend
    re_path(
        frontend_urls.EMAIL_CONFIRMATION,
        ConfirmEmailRedirect.as_view(),
        name='account_confirm_email',
    ),
    re_path(
        frontend_urls.PASSWORD_RESET,
        TemplateView.as_view(),
        name='password_reset_confirm',
    ),
]


if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path(
            'api/docs/coreapi/',
            include_docs_urls(
                title='Langify API',
                description=api_description,
                patterns=api_urlpatterns,
                authentication_classes=[],
                permission_classes=[],
            ),
        ),
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns


if settings.DEBUG or settings.TEST:
    urlpatterns += staticfiles_urlpatterns() + [
        # Serve static files (additionally) at / for Vue.js
        re_path(frontend_urls.STATIC_FILES, serve_static),
        re_path(r'^(?!(api|page)/).*$', home_view, name='home'),
    ]
