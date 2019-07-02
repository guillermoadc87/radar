from django.urls import path
from . import views


app_name = 'cities'

urlpatterns = [
    # city detail view
    path(r'properties/',
        views.PropertyListView.as_view(), name='property_list'),
    path(r'slack_commands/',
        views.slack_commands, name='slack_commands'),
    path(r'slack_events/',
        views.slack_events, name='slack_events'),
]
