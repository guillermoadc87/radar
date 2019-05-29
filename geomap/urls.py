from django.urls import re_path
from . import views

app_name = 'cities'

urlpatterns = [
    # city detail view
    re_path(r'^properties$', views.PropertyListView.as_view(), name='property_list'),
    re_path(r'^interfaces/(?P<ip>.*)$', views.free_interface_command, name='interfaces'),
    re_path(r'^slack/commands/$', views.slack_commands, name='slack_commands'),
    re_path(r'^slack/images/$', views.save_image, name='slack_commands'),

]