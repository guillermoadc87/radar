import math
from django.contrib.gis.db import models
from django_fsm import transition, FSMIntegerField
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from .helper_functions import user_directory_path, get_subnet
from .slack_api import create_channel_with, send_message
from .netbox_api import create_site, create_racks, create_vlans, delete_components, create_device, get_prefix_for, set_prefix_for
from django.db.models.signals import m2m_changed
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.gis.geos import Point

device_type = [
        (('router'), ('Router')),
        (('switch'), ('Switch')),
        (('chassis'), ('Chassis')),
        (('ONT'), ('ONT')),
    ]
os_type = [
        (('cisco_ios'), ('Cisco IOS')),
        (('cisco_xr'), ('Cisco XR')),
        (('nxos'), ('Cisco NXOS')),
    ]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    slack_id = models.CharField(max_length=120, blank=True, null=True)
    position = models.CharField(max_length=120, blank=True, null=True)

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()

class Property(models.Model):
    types = (
        (('New Construction'), ('New Construction')),
        (('Conversion/OverBuild'), ('Conversion/OverBuild'))
    )

    business_units = (
        (('Fision Home'), ('Fision Home')),
        (('Fision Plus'), ('Fision Plus')),
        (('Fision Stay'), ('Fision Stay')),
        (('Fision Encore'), ('Fision Encore')),
        (('Fision Work'), ('Fision Work')),
        (('Fision U'), ('Fision U')),
        (('Demo'), ('Demo')),
    )

    routers = (
        ('7600', '7600'),
        ('ASR9006', 'ASR9006')
    )
    ont = (
        ('G-240G-A', 'G-240G-A'),
        ('G-241G-A', 'G-241G-A'),
    )

    markets = (
        ('SEFL', 'SEFL'),
        ('SWFL', 'SWFL'),
        ('ATL', 'ATL'),
        ('NC/SC', 'NC/SC'),
        ('CFL', 'CFL'),
    )

    name = models.CharField(max_length=120)
    slug = models.SlugField(_('slug'), max_length=150, unique=True, blank=True, null=True)
    units = models.IntegerField(default=1)
    business_unit = models.CharField(max_length=120, choices=business_units, blank=True, null=True)
    address = models.CharField(max_length=200)
    location = models.PointField(blank=True)
    type = models.CharField(max_length=50, choices=types, blank=True, null=True)
    rf_unit = models.BooleanField('RF In-Unit', default=False)
    rf_coa = models.BooleanField('RF COA', default=False)
    coa = models.BooleanField('COA', default=False)
    market = models.CharField(max_length=10, choices=markets)

    #Network
    feeds = models.ManyToManyField('Property', verbose_name='Fed from', related_name='feeding', blank=True)
    main_device = models.ForeignKey('Device', on_delete=models.CASCADE, blank=True, null=True)
    r_loop = models.CharField('LB', max_length=200, blank=True, null=True)

    #GPON
    gpon_feed = models.ForeignKey('Property', on_delete=models.SET_NULL, verbose_name='GPON from',
                                  related_name='gpon_feeds', blank=True, null=True)
    gpon_chassis = models.CharField(max_length=200, blank=True, null=True)
    ont = models.CharField(max_length=200, choices=ont, blank=True, null=True)
    gpon_cards = models.IntegerField(blank=True, null=True)

    #Dates
    published = models.DateField('Published On', blank=True, null=True)
    fiber_ready = models.DateField('Fiber Ready', blank=True, null=True)
    mdf_ready = models.DateField('MDF Ready', blank=True, null=True)
    network_ready = models.DateField('Router Ready', blank=True, null=True)
    gpon_ready = models.DateField('Chassis Ready', blank=True, null=True)
    gear_installed = models.DateField('Gear Installed', blank=True, null=True)
    cross_connect = models.DateField(verbose_name='Cross-Connected', blank=True, null=True)
    sub_id_ready = models.DateField(blank=True, null=True)
    stb_installed = models.DateField(blank=True, null=True)
    mr_cert = models.DateField('MR Cert', blank=True, null=True)
    done = models.DateField('Completed', blank=True, null=True)

    #Subnets
    _iptvcoa = models.CharField('IP TV COA', max_length=200, blank=True, null=True)
    ip_tv = models.CharField('IP TV', max_length=200, blank=True, null=True)
    ip_mgn_ap = models.CharField('IP MGN AP', max_length=200, blank=True, null=True)
    ip_mgn = models.CharField('IP MGN', max_length=200, blank=True, null=True)

    ip_data = models.CharField('IP DATA', max_length=200, blank=True, null=True)
    ip_voice = models.CharField('IP VOICE', max_length=200, blank=True, null=True)

    #Participans
    pm = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='PM'), verbose_name='PM', related_name='pm', blank=True, null=True)
    neteng = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='NETENG'), verbose_name='Network Engineer', related_name='neteng', blank=True, null=True)
    gponeng = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='GPONENG'), verbose_name='GPON Engineer', related_name='gponeng', blank=True, null=True)
    cpm = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='CPM'), verbose_name='CPM', related_name='cpm', blank=True, null=True)
    fe = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='FE'), verbose_name='Field Engineer', related_name='fe', blank=True, null=True)
    cxceng = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='CXCENG'), verbose_name='CXC Engineer', related_name='cxceng', blank=True, null=True)

    #Files
    hld = models.FileField(upload_to=user_directory_path, blank=True, null=True)

    #Slack
    channel_id = models.CharField(unique=True, max_length=120, null=True)

    #Netbox
    netbox_id = models.IntegerField(blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.old_main_device = self.main_device
        self.old_published = self.published

    def get_calculated_value(self, param):
        if not getattr(self, param):
            return getattr(self, param.replace('_', ''))
        return getattr(self, param)

    def publish(self):
        if self.published:
            self.published = timezone.now()
        else:
            self.published = None
        self.save()

    @property
    def hostname(self):
        return '%s-%s' % (self.market, self.slug.upper())

    @property
    def iptvcoa(self):
        prefix = get_prefix_for(self, 'IPTV-COA')

        if not prefix:
            if self.units < 300:
                return '/26'
            else:
                return '/24'
        return prefix

    @iptvcoa.setter
    def iptvcoa(self, value):
        prefix = get_prefix_for(self, 'IPTV-COA')
        if prefix != value:
            set_prefix_for(self, 'IPTV-COA', value)

    @property
    def iptv(self):
        total_units = 0
        connected_prop = self.gpon_feeds.all()
        if connected_prop:
           for prop in connected_prop:
               total_units += prop.units
        total_units += self.units
        total_stb = total_units * 3.5
        return '/' + str(get_subnet(total_stb))

    @property
    def ipdata(self):
        return '/' + str(get_subnet(self.units))

    @property
    def ipmgnap(self):
        return self.iptvcoa

    @property
    def ipmgn(self):
        return '/24'

    @property
    def get_absolute_url(self):
        return reverse('admin:geomap_property_change', args=[self.pk])

    @property
    def link(self):
        return '<a href="/admin/geomap/property/%s/change/">%s</a>' % (self.pk, self.name)

    @property
    def connect(self):
        if self.r_loop:
            return '<a href="/admin/geomap/property/%s/change/connect/">%s</a>' % (self.pk, self.r_loop)
        return None

    @property
    def netbox_url(self):
        if self.netbox_id:
            return '<a href="http://10.0.0.225:8000/dcim/sites/%s">NETBOX</a>' % (self.name)
        return None

    @property
    def popup_desc(self):
        return '%s (%d units) <br> Router: %s LB: <a href="#">%s</a> <br> GPON: %s <br> PON CARDS: %d <br> <a href="/geomap/interfaces/%s">interfaces</a>' % (
        self.link, self.units, self.main_device, self.connect,
        self.gpon_chassis, self.gponcards, self.r_loop)

    @property
    def gponchassis(self):
        if self.gpon_feed:
            return 0
        count = 0
        units = self.units
        while units >= 0:
            count += 1
            units -= 400
        return count

    @property
    def gponcards(self):
        n_cards = self.units / 16 / 15
        if n_cards < 1:
            n_cards = 1
        return math.ceil(n_cards)+1

    def set_unset_action(self, admin, request, action):
        if not getattr(self, action):
            setattr(self, action, timezone.now())
            message = '%s Ready' % (action,)
        else:
            setattr(self, action, None)
            message = '%s Not Ready' % (action,)
        if self.channel_id:
            print('send message')
            send_message(self.channel_id, message)
        admin.message_user(request, message)

    def get_gpon_coord(self):
        if self.gpon_feed:
            return [[self.gpon_feed.location.y, self.gpon_feed.location.x], [self.location.y, self.location.x]]
        return []

    @property
    def get_links(self):
        return [[[self.location.y, self. location.x], [feed.location.y, feed.location.x]] for feed in self.feeds.all()]

    @property
    def status(self):
        status = ""
        if self.done:
            status += " Done"
        elif self.cross_connect:
            status += " CXC"
        elif self.gear_installed:
            status += " GearInstalled"
            if self.fiber_ready:
                status += " FiberReady"
        elif self.mdf_ready or self.network_ready or self.gpon_ready or self.fiber_ready:
            if self.mdf_ready:
                status += " MDFReady"
            if self.network_ready:
                status += " NetReady"
            if self.gpon_ready:
                status += " ChassisReady"
            if self.fiber_ready:
                status += " FiberReady"
        elif self.published:
            status += " Published"
        else:
            status += " New"

        return status.strip().replace(' ', ', ')

    def assign_devices(self, id, not_id=None):
        print('assigning!!!')
        devices = []
        for device in Device.objects.filter(interfaces__connected__device=id):
            if device.id != not_id and not device.router:
                devices.append(device)
        if not devices:
            return

        for device in devices:
            device.prop = self
            device.save()
            self.assign_devices(device.id, not_id=id)

    def save(self, *args, **kwargs):
        if not self.id:
            self.slug = slugify(self.name)
            self.channel_id = create_channel_with(self.name)

        if not self.main_device or self.old_main_device != self.main_device:
            p_dev = Device.objects.filter(prop=self)
            for dev in p_dev:
                dev.prop = None
                dev.save()

            #site_id = create_site(self)

            #if site_id:
            #    self.netbox_id = site_id
        #if self.old_published and not self.published:
        #    delete_components(self)

        #if self.topology and self.old_topology != self.topology:
        #    [device.delete() for device in self.devices.all()]
        #    for td in self.topology.devices.all():
        #        pd = Device.objects.create(model=td.model, os=td.os, type=td.type)
        #        self.devices.add(pd)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Properties'

@receiver(post_save, sender=Property)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if instance.main_device and instance.old_main_device != instance.main_device:
        instance.assign_devices(instance.main_device)

#@receiver(m2m_changed, sender=Property.feeds.through)
#def property_m2m_changed(sender, instance, **kwargs):
#    print(instance.old_published, instance.published, instance.feeds.all())
#    if not instance.old_published and instance.published and instance.feeds.all():
#        create_racks(instance)
#        create_vlans(instance)
#        create_device(instance)

class Device(models.Model):
    prop = models.ForeignKey('Property', verbose_name='Property', on_delete=models.SET_NULL, related_name='devices',
                             blank=True, null=True)
    hostname = models.CharField(max_length=200, blank=True, null=True)
    model = models.CharField(max_length=200, blank=True, null=True)
    mgn = models.GenericIPAddressField('Management', blank=True, null=True)
    router = models.BooleanField(default=False)

    @property
    def int_avail(self):
        return ''

    def __str__(self):
        return f"{self.mgn} - {self.hostname}"

class Interface(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    bundle_id = models.IntegerField(blank=True, null=True)
    connected = models.OneToOneField('Interface', on_delete=models.SET_NULL, related_name='connected_to', blank=True, null=True)
    device = models.ForeignKey('Device', on_delete=models.CASCADE, related_name='interfaces', blank=True, null=True)

    def __str__(self):
        return F"{self.device} - {self.name}"

class Topology(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Device_Type(models.Model):
    topology = models.ForeignKey('Topology', on_delete=models.CASCADE, related_name='devices', blank=True, null=True)
    model = models.CharField(max_length=200, blank=True, null=True)
    os = models.CharField(max_length=120, choices=os_type, null=True)
    type = models.CharField(max_length=120, choices=device_type, null=True)

    def __str__(self):
        return self.model

class Files(models.Model):
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='files')
    image = models.FileField(upload_to=user_directory_path)

