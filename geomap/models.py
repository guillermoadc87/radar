import math
from networkx.drawing.nx_agraph import write_dot
import networkx as nx
import matplotlib.pyplot as plt
from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models.signals import post_save, m2m_changed
from django.dispatch import receiver
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from .helper_functions import user_directory_path, get_subnet, add_to_inventory
from .slack_api import create_channel_with, send_message
from .constants import PROJECT_TYPES, BUSSINESS_UNITS, ROUTER_MODELS, SWITCH_MODELS, NETWORKS, ONT_MODELS, CONTRACT_STATUS, DONT_INCLUDE_MODELS, MARKETS, ISP_TOPOLOGY_PATH

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
    market = models.CharField(max_length=50, choices=MARKETS, blank=True, null=True)
    rf_unit = models.BooleanField('RF In-Unit', default=False)
    rf_coa = models.BooleanField('RF COA', default=False)
    coa = models.BooleanField('COA', default=False)
    off_net = models.BooleanField('Offnet', default=False)
    services = models.TextField(blank=True, null=True)
    contract = models.CharField(max_length=50, choices=CONTRACT_STATUS, blank=True, null=True)

    #Network
    feeds = models.ManyToManyField('Property', verbose_name='Fed from', related_name='feeding', blank=True)
    router = models.CharField(max_length=50, choices=ROUTER_MODELS, blank=True, null=True)
    r_mgn = models.GenericIPAddressField(unique=True, blank=True, null=True)
    switch = models.CharField(max_length=50, choices=SWITCH_MODELS, blank=True, null=True)
    s_mgn = models.GenericIPAddressField(unique=True, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

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
    participants = models.ManyToManyField(User, blank=True)

    #Slack
    channel_id = models.CharField(max_length=120, null=True)

    def __init__(self, *args, **kwargs):
        super(Property, self).__init__(*args, **kwargs)
        self.old_name = self.name
        self.old_r_mgn_ip = self.r_mgn
        self.old_s_mgn_ip = self.s_mgn

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
            status += " MDFGearInstalled"
            if self.fiber_ready:
                status += " OSPReady"
        elif self.mdf_ready or self.network_ready or self.gpon_ready or self.fiber_ready:
            if self.mdf_ready:
                status += " MDFReady"
            if self.network_ready:
                status += " RTRReady"
            if self.gpon_ready:
                status += " OLTReady"
            if self.fiber_ready:
                status += " FiberReady"
        elif self.published:
            status += " Published"
        else:
            status += " New"

        return status.strip().replace(' ', ', ')

    def build_graph(self):
        devices = Device.objects.filter(prop=self)
        #print(self.name, devices)
        graph = nx.MultiGraph()

        graph.add_nodes_from([device.hostname_model_mgn for device in devices])

        edges = []
        for device in devices:
            connected_devices = Device.objects.filter(interfaces__connected__device=device)
            for connected_device in connected_devices:
                edge = tuple(sorted((device.hostname_model_mgn, connected_device.hostname_model_mgn)))
                if edge not in edges:
                    edges.append(edge)
        #print(edges)
        graph.add_edges_from(edges)
        plt.figure(1, figsize=(40, 40))
        pos = nx.spring_layout(graph)
        #write_dot(graph, "grid.dot")
        #pdot = nx.nx_pydot.to_pydot(graph)
        #image = pdot.create_png()
        #if image:
        #    with open(ISP_TOPOLOGY_PATH + 'pydot.png', 'wb') as f:
        #        f.write(image)
        nx.draw_networkx(graph, pos, node_size=1000, node_shape='s')
        plt.savefig(ISP_TOPOLOGY_PATH)
        plt.close()

    def add_devices(self, device, viewed=None):
        if viewed is None:
            viewed = []

        viewed.append(device.id)

        device.prop = self
        device.save()

        connected_devices = Device.objects.filter(~Q(model__in=DONT_INCLUDE_MODELS),
                                                  ~Q(id__in=viewed),
                                                  interfaces__connected__device=device).distinct()
        print(connected_devices)
        for connected_device in connected_devices:
            self.add_devices(connected_device, viewed)

    def remove_devices(self):
        for dev in Device.objects.filter(prop=self):
            dev.prop = None
            dev.save()

    def save(self, *args, **kwargs):
        if not self.id or self.old_name != self.name:
            self.slug = slugify(f"{self.id}-{self.name}")
        if not self.pk:
            self.channel_id = create_channel_with(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Properties'

@receiver(post_save, sender=Property)
def sync_devices(sender, instance, created, **kwargs):
    if not instance.r_mgn or instance.r_mgn != instance.old_r_mgn_ip:
        instance.remove_devices()
    if instance.r_mgn and instance.r_mgn != instance.old_r_mgn_ip:
        try:
            dev = Device.objects.get(mgn=instance.r_mgn)
            instance.add_devices(dev)
        except Device.DoesNotExist:
            pass

#@receiver(m2m_changed, sender=Property.feeds.through)
#def sync_feeds(sender, instance, **kwargs):
    #print(kwargs)
#    for prop in instance.feeds.all():
#        prop.feeds.remove(instance)
#    for prop in instance.feeds.all():
#        prop.feeds.add(instance)
    #print(instance.old_feeds.all())
    #print(instance.feeds.all())

class Device(models.Model):
    hostname = models.CharField(max_length=120)
    mgn = models.GenericIPAddressField(unique=True)
    model = models.CharField(max_length=120, blank=True, null=True)
    node_id = models.IntegerField(blank=True, null=True)
    prop = models.ForeignKey('Property', on_delete=models.SET_NULL, blank=True, null=True)

    @property
    def hostname_model_mgn(self):
        return f"{self.hostname}\n{self.model}\n{self.mgn}"

    def path_to(self, ip, arr, viewed=None):
        if viewed is None:
            viewed = []

        viewed.append(self.id)
        arr.append(self.mgn)

        print(self.hostname, viewed, arr)
        if (self.mgn == ip):
            return True

        devices = Device.objects.filter(~Q(model__in=DONT_INCLUDE_MODELS),
                                        ~Q(id__in=viewed),
                                        interfaces__connected__device=self).distinct()
        for neighbor in devices:
            if neighbor.path_to(ip, arr, viewed):
                return True

        arr.pop(-1)
        return False

    def save(self, *args, **kwargs):
        if not self.pk:
            add_to_inventory(self.mgn)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.mgn} - {self.hostname}'

class Interface(models.Model):
    name = models.CharField(max_length=120, blank=True, null=True)
    description = models.CharField(max_length=120, blank=True, null=True)
    device = models.ForeignKey('Device', on_delete=models.SET_NULL, related_name='interfaces', blank=True, null=True)
    connected = models.OneToOneField('Interface', on_delete=models.SET_NULL, blank=True, null=True)

    def __str__(self):
        return f'{self.name} ({self.device.hostname})'

class Statistics(models.Model):
    interface = models.ForeignKey('Interface', on_delete=models.SET_NULL, blank=True, null=True)
    date = models.DateField()
    maxin = models.FloatField(blank=True, null=True)
    maxout = models.FloatField(blank=True, null=True)

    def __str__(self):
        return f'{self.interface.name} ({self.date})'

class File(models.Model):
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to=user_directory_path)

