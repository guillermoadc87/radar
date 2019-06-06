from django.views.generic import ListView
from .models import Property


class PropertyListView(ListView):
    """
        City detail view.
    """
    template_name = 'geomap.html'
    model = Property
