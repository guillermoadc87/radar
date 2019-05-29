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
from .constants import PROJECT_TYPES, BUSSINESS_UNITS, ROUTER_MODELS, SWITCH_MODELS, NETWORKS, ONT_MODELS, CONTRACT_STATUS

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
    osp_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(_('slug'), max_length=150, unique=True, blank=True, null=True)
    units = models.IntegerField(default=1)
    business_unit = models.CharField(max_length=120, choices=BUSSINESS_UNITS, blank=True, null=True)
    address = models.CharField(max_length=200)
    location = models.PointField(blank=True)
    type = models.CharField(max_length=50, choices=PROJECT_TYPES, blank=True, null=True)
    network = models.CharField(max_length=50, choices=NETWORKS, blank=True, null=True)
    rf_unit = models.BooleanField('RF In-Unit', default=False)
    rf_coa = models.BooleanField('RF COA', default=False)
    coa = models.BooleanField('COA', default=False)
    services = models.TextField(blank=True, null=True)
    contract = models.CharField(max_length=50, choices=CONTRACT_STATUS, blank=True, null=True)

    #Network
    feeds = models.ManyToManyField('Property', verbose_name='Fed from', related_name='feeding', blank=True)
    router = models.CharField(max_length=50, choices=ROUTER_MODELS, blank=True, null=True)
    r_mgn = models.GenericIPAddressField(unique=True, blank=True, null=True)
    switch = models.CharField(max_length=50, choices=SWITCH_MODELS, blank=True, null=True)
    s_mgn = models.GenericIPAddressField(unique=True, blank=True, null=True)

    #GPON
    gpon_feed = models.ForeignKey('Property', on_delete=models.SET_NULL, verbose_name='GPON from',
                                  related_name='gpon_feeds', blank=True, null=True)
    gpon_chassis = models.IntegerField('# Chassis', blank=True, null=True)
    gpon_cards = models.IntegerField('Cards', blank=True, null=True)
    gpon_ont = models.CharField(max_length=120, choices=ONT_MODELS, blank=True, null=True)

    #Dates
    published = models.DateField('Published On', blank=True, null=True)
    fiber_ready = models.DateField('Fiber Ready', blank=True, null=True)
    mdf_ready = models.DateField('MDF Ready', blank=True, null=True)
    network_ready = models.DateField('Router Pickup', blank=True, null=True)
    gpon_ready = models.DateField('Chassis Pickup', blank=True, null=True)
    gear_installed = models.DateField('Installed', blank=True, null=True)
    cross_connect = models.DateField(verbose_name='Cross-Connected', blank=True, null=True)
    sub_id_ready = models.DateField(blank=True, null=True)
    stb_installed = models.DateField(blank=True, null=True)
    mr_cert = models.DateField('MR Cert', blank=True, null=True)
    done = models.DateField('Completed', blank=True, null=True)

    #Subnets
    ip_tv_coa = models.CharField('IP TV COA', max_length=200, blank=True, null=True)
    ip_tv = models.CharField('IP TV', max_length=200, blank=True, null=True)
    ip_data = models.CharField('IP DATA', max_length=200, blank=True, null=True)
    ip_data_bulk = models.CharField('IP DATA BULK', max_length=200, blank=True, null=True)
    ip_voice = models.CharField('IP VOICE', max_length=200, blank=True, null=True)
    ip_mgn_ap = models.CharField('IP MGN AP', max_length=200, blank=True, null=True)
    ip_mgn = models.CharField('IP MGN', max_length=200, blank=True, null=True)
    nomadix_lan = models.CharField('Nomadix LAN', max_length=200, blank=True, null=True)
    nomadix_wan = models.CharField('Nomadix WAN', max_length=200, blank=True, null=True)
    security = models.CharField(max_length=200, blank=True, null=True)

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
    channel_id = models.CharField(max_length=120, null=True)

    def __init__(self, *args, **kwargs):
        super(Property, self).__init__(*args, **kwargs)
        #self.old_mgn_ip = self.mgn_ip

    def get_calculated_value(self, param):
        if not getattr(self, param):
            return getattr(self, param.replace('_', ''))
        return getattr(self, param)

    @property
    def iptvcoa(self):
        if self.units < 300:
            return '/26'
        else:
            return '/24'

    #@property
    #def iptv(self):
    #    total_units = 0
    #    connected_prop = self.feeding.filter(mgn_ip__isnull=True)
    #    connected_prop = connected_prop.union(self.feeds.filter(mgn_ip__isnull=True))
    #    if connected_prop:
    #       for prop in connected_prop:
    #           total_units += prop.units
    #    total_units += self.units
    #    total_stb = total_units * 3.5
    #    return '/' + str(get_subnet(total_stb))

    @property
    def ipdata(self):
        return '/' + str(get_subnet(self.units))

    @property
    def ipmgnap(self):
        return self.iptvcoa

    @property
    def ipmgn(self):
        return self.iptvcoa

    @property
    def link(self):
        return '<a href="/admin/geomap/property/%s/change/">%s</a>' % (self.pk, self.name)

    @property
    def connect(self):
        if self.r_mgn:
            return '<a href="/admin/geomap/property/%s/change/connect/">%s</a>' % (self.pk, self.r_mgn)
        return None

    @property
    def popup_desc(self):
        return '%s (%d units) <br> Router: <a href="#">%s</a> <br> GPON: %d <br> PON CARDS: %d' % (
        self.link, self.units, self.connect,
        self.get_calculated_value('gpon_chassis'), self.get_calculated_value('gpon_cards'))

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

    def add_devices_for(self, device, no_dev_id=None):
        conn_devs = filter(lambda d: d.id != no_dev_id, Device.objects.filter(interfaces__connected__device=device))
        for conn_dev in conn_devs:
            print(conn_dev)
            conn_dev.prop = self
            conn_dev.save()
            self.add_devices_for(conn_dev, no_dev_id=device.id)

    def save(self, *args, **kwargs):
        #if not self.id:
        #    self.slug = slugify(self.name)
        if not self.pk:
            self.channel_id = create_channel_with(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Properties'

#@receiver(post_save, sender=Property)
#def sync_devices(sender, instance, created, **kwargs):
#    if not instance.mgn_ip or instance.mgn_ip != instance.old_mgn_ip:
#        for dev in Device.objects.filter(prop=instance):
#            dev.prop = None
#            dev.save()
#    if instance.mgn_ip:
#        try:
#            dev = Device.objects.get(mgn=instance.mgn_ip)
#            dev.prop = instance
#            dev.save()
#            instance.add_devices_for(dev)
#        except Device.DoesNotExist:
#            pass
#    instance.save()

class Device(models.Model):
    hostname = models.CharField(max_length=120)
    mgn = models.GenericIPAddressField(unique=True)
    model = models.CharField(max_length=120, blank=True, null=True)
    node_id = models.IntegerField(blank=True, null=True)
    prop = models.ForeignKey('Property', on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f'{self.mgn} - {self.hostname}'

class Interface(models.Model):
    name = models.CharField(max_length=120, blank=True, null=True)
    status = models.CharField(max_length=120, blank=True, null=True)
    device = models.ForeignKey('Device', on_delete=models.SET_NULL, related_name='interfaces', blank=True, null=True)
    connected = models.OneToOneField('Interface', on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f'{self.name} ({self.device.hostname})'

class Statistics(models.Model):
    interface = models.ForeignKey('Interface', on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateField()
    maxin = models.FloatField()
    maxout = models.FloatField()

class File(models.Model):
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='files')
    image = models.FileField(upload_to=user_directory_path)

