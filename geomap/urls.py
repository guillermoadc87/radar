from django.urls import re_path
from . import views


app_name = 'cities'

urlpatterns = [
    # city detail view
    re_path(r'^properties$',
        views.PropertyListView.as_view(), name='property_list'),
]