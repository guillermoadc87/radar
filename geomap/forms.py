from django import forms
from .models import Property
import googlemaps
from django.contrib.gis.geos import Point

class PropertyForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):

        instance = kwargs.get('instance', 0)
        if instance:
            instance.ip_tv_coa = self.get_subnet_for(instance, 'ip_tv_coa')
            instance.ip_tv = self.get_subnet_for(instance, 'ip_tv')
            instance.ip_data = self.get_subnet_for(instance, 'ip_data')
            instance.ip_mgn_ap = self.get_subnet_for(instance, 'ip_mgn_ap')
            instance.ip_mgn = self.get_subnet_for(instance, 'ip_mgn')

        super(PropertyForm, self).__init__(*args, **kwargs)

        if instance:
            obj = Property.objects.get(id=instance.id)
            pk_list = obj.feeding.all().values_list('pk', flat=True)
            self.fields["feeds"].queryset = Property.objects.exclude(pk__in=pk_list).order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        address = cleaned_data['address']

        gmaps = googlemaps.Client(key='AIzaSyDbPjoUnqsFrFhzzB3Q3AuXwrF2cD9v2sI')
        geocode_result = gmaps.geocode(address)

        if not geocode_result:
            raise forms.ValidationError("Address not valid!")

        lng = geocode_result[0]['geometry']['location']['lng']
        lat = geocode_result[0]['geometry']['location']['lat']
        cleaned_data['location'] = Point(lng, lat)
        return cleaned_data

    def get_subnet_for(self, instance, param):
        if not getattr(instance, param):
            return '/' + str(getattr(instance, param.replace('_', '')))
        return getattr(instance, param)

    class Meta:
        model = Property
        widgets = {'location': forms.HiddenInput()}
        exclude = []