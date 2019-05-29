import re
import googlemaps
from .helper_functions import ping_test
from django import forms
from .models import Property, Device, device_type
from .netbox_api import get_device_types, get_tags_of_device
from django.contrib.gis.geos import Point

south_florida = ['Miami', 'Hialeah', 'Fort Lauderdale', 'Port St. Lucie', 'Pembroke Pines', 'Hollywood, Miramar', 'Coral Springs', 'Miami Gardens', 'West Palm Beach', 'Pompano Beach', 'Davie', 'Miami Beach', 'Plantation', 'Sunrise', 'Boca Raton', 'Deerfield Beach', 'Boynton Beach', 'Lauderhill', 'Weston', 'Delray Beach', 'Homestead', 'Tamarac', 'North Miami', 'Wellington', 'Jupiter', 'Margate', 'Coconut',]
southwest_florida = ['Punta Gorda', 'East Naples', 'Arcadia', 'Moore Haven', 'LaBelle', 'Fort Myers', 'Bradenton', 'Sarasota']
central_florida = ['Tampa', 'St. Petersburg', 'Orlando', 'Clearwater', 'Palm Bay', 'Lakeland', 'Deltona', 'Largo', 'Melbourne', 'Daytona Beach', 'Kissimmee', 'Port Orange', 'Sanford', 'Clermont', 'Leesburg']

class PropertyForm(forms.ModelForm):
    equipment = forms.ChoiceField(required=False)
    card = forms.ChoiceField(required=False)
    rsp = forms.ChoiceField(required=False)
    gpon_chassis = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):

        self.instance = kwargs.get('instance', 0)
        #if self.instance:
            #self.instance.ip_tv_coa = self.instance.get_calculated_value('ip_tv_coa')
            #self.instance.ip_tv = self.instance.get_calculated_value('ip_tv')
            #self.instance.ip_data = self.instance.get_calculated_value('ip_data')
            #self.instance.ip_mgn_ap = self.instance.get_calculated_value('ip_mgn_ap')
            #self.instance.ip_mgn = self.instance.get_calculated_value('ip_mgn')

        super(PropertyForm, self).__init__(*args, **kwargs)
        self.fields["equipment"].choices = get_device_types(tags=['router', 'switch'])
        self.fields["gpon_chassis"].choices = get_device_types(tags=['chassis'])

        self.fields["feeds"].queryset = self.fields["feeds"].queryset.order_by('name')
        self.fields["gpon_feed"].queryset = self.fields["gpon_feed"].queryset.order_by('name')

        if self.instance and self.instance.id and not self.instance.published:
            obj = Property.objects.get(id=self.instance.id)
            pk_list = obj.feeding.all().values_list('pk', flat=True)
            self.fields["feeds"].queryset = self.fields["feeds"].queryset.exclude(pk__in=pk_list)
            self.fields["gpon_feed"].queryset = self.fields["gpon_feed"].queryset.exclude(pk__in=pk_list)

    def clean(self):
        cleaned_data = super().clean()
        published = cleaned_data.get('published')
        fiber_ready = cleaned_data.get('fiber_ready')
        mdf_ready = cleaned_data.get('mdf_ready')
        network_ready = cleaned_data['network_ready']
        gpon_ready = cleaned_data['gpon_ready']

        if (fiber_ready or mdf_ready or network_ready or gpon_ready) and not published:
            raise forms.ValidationError("The property needs to be Published")
        if fiber_ready and fiber_ready < published:
            raise forms.ValidationError("Fiber Ready needs to happen after Published")
        if mdf_ready and mdf_ready < published:
            raise forms.ValidationError("MDF Ready needs to happen after Published")
        if network_ready and network_ready < published:
            raise forms.ValidationError("Nerwork Ready needs to happen after Published")
        if gpon_ready and gpon_ready < published:
            raise forms.ValidationError("GPON Ready needs to happen after Published")

        gear_installed = cleaned_data.get('gear_installed')

        if gear_installed and (not network_ready or not gpon_ready):
            raise forms.ValidationError("Gear not Ready for Installing")
        if gear_installed and gear_installed < network_ready:
            raise forms.ValidationError("Gear can't be installed before Router Configuration")
        if gear_installed and gear_installed < gpon_ready:
            raise forms.ValidationError("Gear can't be installed before GPON Configuration")

        cross_connect = cleaned_data.get('cross_connect')

        if cross_connect and not gear_installed:
            raise forms.ValidationError("Gear needs to be Installed")
        if cross_connect and cross_connect < gear_installed:
            raise forms.ValidationError("CXC can't happen before Gear Install")

        done = cleaned_data.get('done')

        if done and not cross_connect:
            raise forms.ValidationError("Needs to be CXC")
        if done and done < cross_connect:
            raise forms.ValidationError("Cant be Completed before is CXC")

        #Validate Address
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

        cleaned_data['location'] = Point(lng, lat)
        cleaned_data['address'] = geocode_result[0]['formatted_address']

        city = ''
        state = ''
        for item in geocode_result[0]['address_components']:
            if item.get('types') and 'administrative_area_level_1' in item.get('types'):
                state = item.get('short_name')
            elif item.get('types') and 'locality' in item.get('types'):
                city = item.get('short_name')

        if state in ['NC', 'SC']:
            cleaned_data['market'] = 'NC/SC'
        elif city in south_florida:
            cleaned_data['market'] = 'SEFL'
        elif city in southwest_florida:
            cleaned_data['market'] = 'SWFL'
        elif city in central_florida:
            cleaned_data['market'] = 'CFL'
        elif state in ['GA']:
            cleaned_data['market'] = 'ATL'
        elif state in ['PA']:
            cleaned_data['market'] = 'PA'

        #Validation code after publishing
        if published:
            market = cleaned_data.get('market')

            if not market:
                raise forms.ValidationError("Define the market before publishing")

            main_device = cleaned_data.get('main_device')

            if not main_device:
                raise forms.ValidationError("Define the networking main device before publishing")

            ont = cleaned_data.get('ont')

            if not ont:
                raise forms.ValidationError("Define the ont platform before publishing")

            feeds = cleaned_data.get('feeds')

            if not feeds:
                raise forms.ValidationError("Define the property feeds before publishing")

            #tags = get_tags_of_device(equipment)

            #if not 'router' in tags and 'switch' in tags and feeds.count() > 1:
            #    raise forms.ValidationError("A Property with no router can only have one feed")

            #gpon_chassis = cleaned_data.get('gpon_chassis')

            #if 'router' in tags and not gpon_chassis:
            #    raise forms.ValidationError("Define the gpon platform before publishing")

        return cleaned_data

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        print(form.instance.feeds.all())

    class Meta:
        model = Property
        widgets = {'location': forms.HiddenInput()}
        exclude = []


class DeviceForm(forms.ModelForm):
    model = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(DeviceForm, self).__init__(*args, **kwargs)
        self.fields["model"].choices = get_device_types(tags=['router', 'switch', 'chassis'])
        #self.fields["prop"].queryset = self.fields["prop"].queryset.order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        model = cleaned_data.get('model')

        tags = get_tags_of_device(model)
        if tags:
            tag = tags[0]
            t = list(filter(lambda x: x[0] == tag, device_type))
            if t:
                cleaned_data['type'] = t[0]
            else:
                raise forms.ValidationError("tag in Netbox can only be the following %s (%s)" % (", ".join(map(lambda x: x[0], Device.equiment_type), tag)))
        else:
            raise forms.ValidationError("Specify a tag in Netbox for this device type")

        installed = cleaned_data.get('installed')
        loopback = cleaned_data.get('loopback')

        if installed and not loopback:
            raise forms.ValidationError("Specify LP to test connectivity")
        elif installed and loopback:
            ping = ping_test(loopback)
            if not ping:
                raise forms.ValidationError("The device is not reachable")

    class Meta:
        model = Device
        exclude = ['type']

class Device_TypeForm(forms.ModelForm):
    model = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(Device_TypeForm, self).__init__(*args, **kwargs)
        self.fields["model"].choices = get_device_types(tags=['router', 'switch', 'chassis'])
        #self.fields["prop"].queryset = self.fields["prop"].queryset.order_by('name')

    def clean(self):
        cleaned_data = super().clean()
        model = cleaned_data.get('model')

        tags = get_tags_of_device(model)
        if tags:
            tag = tags[0]
            t = list(filter(lambda x: x[0] == tag, device_type))
            if t:
                cleaned_data['type'] = t[0]
            else:
                raise forms.ValidationError("tag in Netbox can only be the following %s (%s)" % (", ".join(map(lambda x: x[0], Device.equiment_type), tag)))
        else:
            raise forms.ValidationError("Specify a tag in Netbox for this device type")

    class Meta:
        model = Device
        exclude = ['type']
