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
    switches = (
        ('2960', '2960'),
        ('ASR920', 'ASR920')
    )

    STATUS_CREATED = 0
    STATUS_PUBLISHED = 1
    STATUS_RFI = 2
    STATUS_RFC = 3
    STATUS_RMR = 4
    STATUS_COMPLETED = 5
    STATUS_CHOICES = (
        (STATUS_CREATED, 'Created'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_RFI, 'Ready for Installs'),
        (STATUS_RFC, 'Ready for CXC'),
        (STATUS_RMR, 'Ready for MR'),
        (STATUS_COMPLETED, 'Completed'),
    )

    osp_id = models.IntegerField(blank=True, null=True)
    name = models.CharField(max_length=120)
    slug = models.SlugField(_('slug'), max_length=150, unique=True, blank=True, null=True)
    units = models.IntegerField(default=1)
    business_unit = models.CharField(max_length=120, choices=business_units, blank=True, null=True)
    address = models.CharField(max_length=200)
    location = models.PointField(blank=True)
    status = FSMIntegerField(choices=STATUS_CHOICES, default=STATUS_CREATED, protected=True)
    type = models.CharField(max_length=50, choices=types, blank=True, null=True)

    rf_unit = models.BooleanField('RF In-Unit', default=False)
    rf_coa = models.BooleanField('RF COA', default=False)
    coa = models.BooleanField('COA', default=False)

    feeds = models.ManyToManyField('Property', verbose_name='Fed from', related_name='feeding', blank=True)
    gpon_feed = models.ForeignKey('Property', on_delete=models.SET_NULL, verbose_name='GPON from', related_name='gpon_feeds', blank=True, null=True)
    router = models.CharField(max_length=200, choices=routers, blank=True, null=True)
    r_loop = models.CharField('LB', max_length=200, blank=True, null=True)
    switch = models.CharField(max_length=200, choices=switches, blank=True, null=True)
    s_loop = models.CharField('Switch LB', max_length=200, blank=True, null=True)

    #Dates
    published = models.DateField('Published On', blank=True, null=True)
    fiber_ready = models.DateField('Fiber Ready', blank=True, null=True)
    mdf_ready = models.DateField('MDF Ready', blank=True, null=True)
    network_ready = models.DateField('Ready For Pickup', blank=True, null=True)
    gpon_ready = models.DateField('Ready For Pickup', blank=True, null=True)
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
    ip_voice = models.CharField('IP VOICE', max_length=200, blank=True, null=True)
    ip_mgn_ap = models.CharField('IP MGN AP', max_length=200, blank=True, null=True)
    ip_mgn = models.CharField('IP MGN', max_length=200, blank=True, null=True)

    #Participans
    pm = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='PM'), verbose_name='PM', related_name='pm', blank=True, null=True)
    neteng = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='NETENG'), verbose_name='Network Engineer', related_name='neteng', blank=True, null=True)
    gponeng = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='GPONENG'), verbose_name='GPON Engineer', related_name='gponeng', blank=True, null=True)
    cpm = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='CPM'), verbose_name='CPM', related_name='cpm', blank=True, null=True)
    fe = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='FE'), verbose_name='Field Engineer', related_name='fe', blank=True, null=True)
    cxceng = models.ForeignKey(User, on_delete=models.SET_NULL, limit_choices_to=Q(groups__name='CXCENG'), verbose_name='CXC Engineer', related_name='cxceng', blank=True, null=True)

    #Files
    hld = models.FileField(upload_to=user_directory_path, blank=True, null=True)

    @property
    def iptvcoa(self):
        if self.units < 300:
            return 26
        else:
            return 24

    @property
    def iptv(self):
        total_units = 0
        feeding_prop = self.feeding.filter(router__isnull=True)
        if feeding_prop:
           for prop in feeding_prop:
               total_units += prop.units
        total_units += self.units
        total_stb = total_units * 3.5
        return get_subnet(total_stb)

    @property
    def ipdata(self):
        return get_subnet(self.units)

    @property
    def ipmgnap(self):
        return self.iptvcoa

    @property
    def ipmgn(self):
        return self.iptvcoa

    @property
    def popup_desc(self):
        return '%s (%d units) <br> Router: %s LB: <a href="#">%s</a> <br> Switch: %s LB: %s <br> GPON: %d <br> PON CARDS: %d' % (self.name, self.units, self.router, self.r_loop, self.switch, self.s_loop, self.gpon_chassis, self.gpon_cards)

    @property
    def gpon_chassis(self):
        if self.gpon_feed:
            return 0
        count = 0
        units = self.units
        while units >= 0:
            count += 1
            units -= 400
        return count

    @property
    def gpon_cards(self):
        n_cards = self.units / 16 / 15
        if n_cards < 1:
            n_cards = 1
        return round(n_cards)+1

    def set_unset_action(self, action):
        if not getattr(self, action):
            setattr(self, action, timezone.now())
        else:
            setattr(self, action, None)

    def get_gpon_coord(self):
        if self.gpon_feed:
            return [[self.gpon_feed.location.y, self.gpon_feed.location.x], [self.location.y, self.location.x]]
        return []

    def get_links(self):
        return [[[self.location.y, self. location.x], [feed.location.y, feed.location.x]] for feed in self.feeds.all()]



    def save(self, *args, **kwargs):
        #if not self.id:
        #    self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'Properties'


class Equiment(models.Model):
    equiment_type = [
        (('Router'), ('Router')),
        (('Switch'), ('Switch')),
        (('OLT'), ('OLT')),
        (('ONT'), ('ONT')),
    ]
    hostname = models.CharField(max_length=120)
    loopback = models.GenericIPAddressField()
    type = models.CharField(max_length=120, choices=equiment_type, null=True)

class File(models.Model):
    property = models.ForeignKey('Property', on_delete=models.CASCADE, related_name='files')
    image = models.FileField(upload_to=user_directory_path)

