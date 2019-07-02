from django import forms
from datetime import datetime
from .models import Property, Interface, Device
import googlemaps
from django.contrib.gis.geos import Point
from .nornir_api import get_available_vlans_for, get_available_interfaces_for
from .helper_functions import not_pingable

class SubnetProvisioningForm(forms.Form):
    vlan = forms.ChoiceField(required=True)
    subnet = forms.CharField(required=True)
    description = forms.CharField(required=True)
    port = forms.ChoiceField(required=True)
    ip = forms.CharField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        initial_ip = kwargs.pop('ip')
        super(SubnetProvisioningForm, self).__init__(*args, **kwargs)
        if initial_ip:
            self.fields["vlan"].choices = [(vlan, vlan) for vlan in get_available_vlans_for(initial_ip)]
            self.fields["port"].choices = [(ports, ports) for ports in get_available_interfaces_for(initial_ip)]
            self.fields["ip"].initial = initial_ip

class BUGraphForm(forms.Form):
    YEARS = [year for year in range(datetime.now().year-2, datetime.now().year+1)]
    #interface_choices = [(interface.id, interface.name) for interface in Interface.objects.all()]

    start = forms.DateField(widget=forms.SelectDateWidget(years=YEARS), required=True, initial=datetime.now())
    end = forms.DateField(widget=forms.SelectDateWidget(years=YEARS), required=True, initial=datetime.now())
    interfaces = forms.MultipleChoiceField(required=True)

    def __init__(self, *args, **kwargs):
        super(BUGraphForm, self).__init__(*args, **kwargs)
        self.fields["interfaces"].choices = [(interface.id, interface.name) for interface in Interface.objects.all()]

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data['start']
        end = cleaned_data['end']

        if start and end:
            if start > end:
                raise forms.ValidationError("Start date has to be before end date")

class DeviceForm(forms.ModelForm):
    model = forms.ChoiceField()

    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        models = Device.objects.all().values_list('model', flat=True).distinct().order_by('model')
        self.fields["model"].choices = [(model, model) for model in models]

    def clean(self):
        cleaned_data = super().clean()
        if not_pingable(cleaned_data['mgn']):
            raise forms.ValidationError("Not able to ping the IP: " + cleaned_data['mgn'])

    class Meta:
        model = Device
        exclude = []

class PropertyForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):

        instance = kwargs.get('instance', 0)
        if instance:
            instance.gpon_chassis = instance.get_calculated_value('gpon_chassis')
            instance.gpon_cards = instance.get_calculated_value('gpon_cards')

            instance.ip_tv_coa = instance.get_calculated_value('ip_tv_coa')
            #instance.ip_tv = instance.get_calculated_value('ip_tv')
            instance.ip_data = instance.get_calculated_value('ip_data')
            instance.ip_mgn_ap = instance.get_calculated_value('ip_mgn_ap')
            instance.ip_mgn = instance.get_calculated_value('ip_mgn')

        super(PropertyForm, self).__init__(*args, **kwargs)

        if instance:
            obj = Property.objects.get(id=instance.id)
            pk_list = obj.feeding.all().values_list('pk', flat=True)
            self.fields["feeds"].queryset = self.fields["feeds"].queryset.order_by('name')
            self.fields["gpon_feed"].queryset = Property.objects.order_by('name')

    def clean(self):
        cleaned_data = super().clean()

        address = cleaned_data.get('address', None)

        gmaps = googlemaps.Client(key='AIzaSyDbPjoUnqsFrFhzzB3Q3AuXwrF2cD9v2sI')

        try:
            geocode_result = gmaps.geocode(address)
        except:
            geocode_result = None

        if not geocode_result:
            raise forms.ValidationError("Invalid Address")

        lng = geocode_result[0]['geometry']['location']['lng']
        lat = geocode_result[0]['geometry']['location']['lat']
        cleaned_data['address'] = geocode_result[0]['formatted_address']
        cleaned_data['location'] = Point(lng, lat)
        #print(cleaned_data['location'])
        published = cleaned_data.get('published')
        fiber_ready = cleaned_data.get('fiber_ready')
        mdf_ready = cleaned_data.get('mdf_ready')
        network_ready = cleaned_data['network_ready']
        gpon_ready = cleaned_data['gpon_ready']

        if (fiber_ready or mdf_ready or network_ready or gpon_ready) and not published:
            raise forms.ValidationError("The property needs to be Published")
        if fiber_ready and fiber_ready < published:
            raise forms.ValidationError("Fiber Ready needs to happen after Published")
        if mdf_ready and mdf_ready < published :
            raise forms.ValidationError("MDF Ready needs to happen after Published")
        if network_ready and network_ready < published:
            raise forms.ValidationError("Nerwork Ready needs to happen after Published")
        if gpon_ready and gpon_ready < published:
            raise forms.ValidationError("GPON Ready needs to happen after Published")

        gear_installed = cleaned_data['gear_installed']

        if gear_installed and (not network_ready or not gpon_ready):
            raise forms.ValidationError("Gear not Ready for Installing")
        if gear_installed and gear_installed < network_ready:
            raise forms.ValidationError("Gear can't be installed before Router Configuration")
        if gear_installed and gear_installed < gpon_ready:
            raise forms.ValidationError("Gear can't be installed before GPON Configuration")

        cross_connect = cleaned_data['cross_connect']

        if cross_connect and not gear_installed:
            raise forms.ValidationError("Gear needs to be Installed")
        if cross_connect and cross_connect < gear_installed:
            raise forms.ValidationError("CXC can't happen before Gear Install")

        done = cleaned_data.get('done')

        if done and not cross_connect:
            raise forms.ValidationError("Needs to be CXC")
        if done and done < cross_connect:
            raise forms.ValidationError("Cant be Completed before is CXC")

        return cleaned_data

    class Meta:
        model = Property
        widgets = {'location': forms.HiddenInput()}
        exclude = []