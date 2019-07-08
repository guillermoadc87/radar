from geomap.models import Property

# Create your models here.
class PropertySummary(Property):
    class Meta:
        proxy = True
        verbose_name = 'Property Summary'
        verbose_name_plural = 'Property Summary'