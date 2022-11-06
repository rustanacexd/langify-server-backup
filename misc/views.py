import datetime
import statistics
from collections import OrderedDict

import pandas as pd
import plotly.graph_objs as go
import plotly.offline as py
from plotly import tools
from rest_framework.exceptions import MethodNotAllowed

from base.constants import SYSTEM_USERS
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import RedirectView, TemplateView
from django.views.generic.detail import DetailView
from frontend_urls import EMAIL_CONFIRMATION
from panta.models import HistoricalTranslatedSegment
from path.models import User

from .models import Page


def home_view(request, *args):
    if request.method == 'GET':
        path = request.get_full_path()
        return redirect('http://localhost:3000{}'.format(path))
    raise MethodNotAllowed(request.method)


class ConfirmEmailRedirect(RedirectView):
    query_string = True
    url = '//localhost:8080/{}%(key)s'.format(
        EMAIL_CONFIRMATION.split('(', maxsplit=1)[0].strip('^')
    )


# Currently not used
def static_view(request, path, static_file):
    if request.method == 'GET':
        if path == 'css':
            content_type = 'text/css'
        elif path == 'js':
            content_type = 'text/javascript'
        else:
            content_type = 'text/html'
        return render(
            request,
            '{}/{}'.format(path, static_file),
            content_type=content_type,
        )
    raise MethodNotAllowed(request.method)


class PageView(DetailView):

    model = Page


class ContactRedirect(HttpResponseRedirect):
    allowed_schemes = ['mailto']


class PageContactView(RedirectView):
    def get(self, request, *args, **kwargs):
        url = self.get_redirect_url(*args, **kwargs)
        return ContactRedirect(url)

    def get_redirect_url(self, slug, index):
        page = get_object_or_404(
            Page.objects.only('protected'), slug=slug, protected__len__gt=index
        )
        return 'mailto:{}'.format(page.protected[index])


class StatisticsView(PermissionRequiredMixin, TemplateView):
    """
    Internal statistics for growth and value.
    """

    template_name = 'misc/statistics.html'
    permission_required = 'misc.view_page'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Days
        start = datetime.date(2017, 12, 20)
        days = (datetime.date.today() - start).days + 1
        dates = [start + datetime.timedelta(i) for i in range(days)]
        context['dates'] = [date.isoformat() for date in dates]
        index = pd.date_range(start, datetime.date.today())

        # Sign ups
        users = (
            User.objects.filter(is_active=True)
            .extra({'date': 'date(date_joined)'})
            .values_list('date', flat=True)
        )
        sign_ups = OrderedDict((date, 0) for date in dates)
        sign_ups_total = 0
        for date in users:
            sign_ups[date] += 1
            sign_ups_total += 1
        context['sign_ups_total'] = sign_ups_total
        sign_ups_per_day = go.Scatter(
            x=index,
            y=tuple(sign_ups.values()),
            mode='lines',
            name='Sign ups per day',
        )

        # Translations
        translations = (
            HistoricalTranslatedSegment.objects.exclude(
                history_user__username__in=SYSTEM_USERS
            )
            .extra({'date': 'date(history_date)'})
            .values('date', 'history_user_id')
        )
        per_day = OrderedDict((date, 0) for date in dates)
        per_user = OrderedDict((date, {}) for date in dates)
        translations_total = 0
        for obj in translations:
            # Per day
            per_day[obj['date']] += 1
            # Total
            translations_total += 1
            # Per day and user
            date = per_user[obj['date']]
            try:
                date[obj['history_user_id']] += 1
            except KeyError:
                date[obj['history_user_id']] = 1
        translations_per_user_per_day = [
            statistics.mean(usrs.values() or [0]) for usrs in per_user.values()
        ]
        context['translations_total'] = translations_total
        ai_total = HistoricalTranslatedSegment.objects.filter(
            history_user__username='AI'
        ).count()
        context['ai_translations_total'] = ai_total
        translations_per_day = go.Scatter(
            x=index,
            y=tuple(per_day.values()),
            mode='lines',
            name='Edits per day',
        )
        translations_per_user_per_day = go.Scatter(
            x=index,
            y=translations_per_user_per_day,
            mode='lines',
            name='Edits per user and day',
        )

        # Usage
        translations = pd.DataFrame(translations)
        translations['week'] = translations['date'].apply(
            lambda date: date - datetime.timedelta(days=date.weekday())
        )
        translations['month'] = translations['date'].apply(
            lambda date: date.replace(day=1)
        )
        days = (
            translations.drop_duplicates(['date', 'history_user_id'])
            .groupby(['date'])
            .count()
            .reindex(index, fill_value=0)
        )
        weeks = (
            translations.drop_duplicates(['week', 'history_user_id'])
            .groupby(['week'])
            .count()
            .reindex(index)
            .ffill()
        )
        months = (
            translations.drop_duplicates(['month', 'history_user_id'])
            .groupby(['month'])
            .count()
            .reindex(index)
            .ffill()
        )
        users_per_day = go.Scatter(
            x=index, y=days.history_user_id, mode='lines', name='Users per day'
        )
        users_per_week = go.Scatter(
            x=index,
            y=weeks.history_user_id,
            mode='lines',
            name='Users per week',
        )
        users_per_month = go.Scatter(
            x=index,
            y=months.history_user_id,
            mode='lines',
            name='Users per month',
        )

        # Plot
        # We could show hover info in all subplots with
        # https://community.plot.ly/t/how-to-code-to-get-all-the-stacked-
        # datapoint-on-mouse-hovering-of-x-axis-shared-charts-in-python-plotly/
        # 11384
        fig = tools.make_subplots(
            rows=3,
            cols=1,
            specs=[[{}], [{}], [{}]],
            shared_xaxes=True,
            vertical_spacing=0.05,
            print_grid=False,
        )
        fig.append_trace(sign_ups_per_day, 1, 1)
        fig.append_trace(translations_per_day, 2, 1)
        fig.append_trace(translations_per_user_per_day, 2, 1)
        fig.append_trace(users_per_day, 3, 1)
        fig.append_trace(users_per_week, 3, 1)
        fig.append_trace(users_per_month, 3, 1)
        fig['layout'].update(title='Ellen4all statistics', height=1000)

        context['plot'] = py.plot(
            fig,
            output_type='div',
            include_plotlyjs=False,
            config={'displaylogo': False},
        )

        return context
