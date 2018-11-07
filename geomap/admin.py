from django.utils import timezone
from django.contrib import admin
from .models import Property
from .views import PropertyListView
from django.urls import re_path, path
from django.utils.html import format_html
from django.urls  import reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.db.models import Q
from .forms import PropertyForm

admin.site.site_header = 'HWC Launcher'
admin.site.site_title = "HWC Launcher"

class PropertyAdmin(admin.ModelAdmin):
    form = PropertyForm
    search_fields = ('name',)
    list_display = ('name', 'units', 'address', 'mr_cert', 'status', 'account_actions')
    readonly_fields = ('iptv', 'ipdata', 'gpon_chassis', 'gpon_cards')
    ordering = ('-mr_cert',)
    filter_horizontal = ('feeds',)
    fieldsets = (
        ('Circuit', {
            'fields': (
                'name',
                'address',
                'location',
                ('units', 'business_unit', 'type',),
                ('rf_unit', 'rf_coa', 'coa',),
            )
        }),
        ('Technology', {
            'fields': (
                'feeds',
                ('gpon_feed', 'router', 'r_loop'),
                ('switch', 's_loop'),
                ('gpon_chassis', 'gpon_cards'),
            )
        }),
        ('Subnets', {
            'fields': (
                ('ip_tv_coa', 'ip_tv', 'ip_voice'),
                ('ip_data', 'ip_mgn', 'ip_mgn_ap'),
            )
        }),
        ('Dates', {
            'fields': (
                ('published', 'fiber_ready', 'network_ready', 'gpon_ready', 'gear_installed', 'cross_connect', 'mr_cert'),
            )
        }),
        ('Files', {
            'fields': ('hld',),
        }),
        ('Participants', {
            'fields': ('pm', 'neteng', 'gponeng', 'cpm', 'fe', 'cxceng',),
        }),
    )

    def iptv(self, obj):
        return obj.iptv
    iptv.allow_tags = True
    iptv.short_description = 'IP TV'

    def ipdata(self, obj):
        return obj.ipdata
    ipdata.allow_tags = True
    ipdata.short_description = 'IP DATA'

    def gpon_chassis(self, obj):
        return obj.gpon_chassis
    gpon_chassis.allow_tags = True
    gpon_chassis.short_description = 'GPON Chassis'

    def gpon_cards(self, obj):
        return obj.gpon_cards
    gpon_cards.allow_tags = True
    gpon_cards.short_description = 'GPON Cards'

    def account_actions(self, obj):
        groups = self.request.user.groups.all()
        if 'CPM' in groups:
            button = format_html(
                '<a class="button" href="{}">Fiber Ready</a>&nbsp;',
                '<a class="button" href="{}">MDF Ready</a>&nbsp;',
                reverse('admin:fiber_ready', args=[obj.pk]),
                reverse('admin:mdf_ready', args=[obj.pk]),
            )
        elif 'NETENG' in groups or 'GPONENG' in groups:
            button = format_html(
                '<a class="button" href="{}">Configured</a>&nbsp;',
                reverse('admin:network_ready', args=[obj.pk]),
            )
        elif 'GPONENG' in groups or 'GPONENG' in groups:
            button = format_html(
                '<a class="button" href="{}">Configured</a>&nbsp;',
                reverse('admin:gpon_ready', args=[obj.pk]),
            )
        elif 'FE' in groups:
            button = format_html(
                '<a class="button" href="{}">Installed</a>&nbsp;',
                reverse('admin:set_date', args=[obj.pk]),
            )
        elif 'CXCENG' in groups:
            button = format_html(
                '<a class="button" href="{}">Cross-Connected</a>&nbsp;',
                reverse('admin:set_date', args=[obj.pk]),
            )
        elif 'PM' in groups:
            button = format_html(
                '<a class="button" href="{}">Publish</a>&nbsp;',
                '<a class="button" href="{}">Done</a>&nbsp;',
                reverse('admin:publish', args=[obj.pk]),
                reverse('admin:done', args=[obj.pk]),
            )
        else:
            button = 'None'
        return button
    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "gpon_feed":
            kwargs["queryset"] = Property.objects.order_by('name')
        return super(PropertyAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "feeds":
            kwargs["queryset"] = Property.objects.order_by('name')
        return super(PropertyAdmin, self).formfield_for_manytomany(db_field, request, **kwargs)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('map/', self.admin_site.admin_view(PropertyListView.as_view()), name='property_list'),
            re_path('set_date/(?P<property_id>\d+)', self.admin_site.admin_view(self.set_date), name='set_date'),
            re_path('map/(?P<property_id>\d+)', self.admin_site.admin_view(self.property_map), name='property_map'),
            re_path('published/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'published'}, name='publish'),
            re_path('fiber_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'fiber_ready'},
                    name='fiber_ready'),
            re_path('mdf_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'mdf_ready'},
                    name='mdf_ready'),
            re_path('network_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'network_ready'},
                    name='network_ready'),
            re_path('gpon_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'gpon_ready'},
                    name='gpon_ready'),
            re_path('gear_installed/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'gear_installed'},
                    name='gear_installed'),
            re_path('cross_connect/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'cross_connect'},
                    name='cross_connect'),
            re_path('mr_cert/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'mr_cert'},
                    name='done'),
            re_path('done/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'done'},
                    name='done'),
        ]
        return my_urls + urls

    def get_queryset(self, request):
        self.request = request
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs
        elif not request.user.groups.all():
            return qs.none()
        else:
            groups = [group.name for group in request.user.groups.all()]
            if 'PM' not in groups:
                qs = qs.filter(published__isnull=False)
            return qs.filter(Q(neteng=request.user) | Q(gponeng=request.user) | Q(cpm=request.user) | Q(fe=request.user) | Q(cxceng=request.user))

    def set_date(self, request, property_id):
        if not request.user.groups:
            self.message_user('User need to be in a valid group')
            return HttpResponseRedirect(".")

        prop = self.get_object(request, property_id)

        groups = [group.name for group in request.user.groups.all()]

        if 'CPM' in groups:
            if not prop.fiber_ready:
                prop.fiber_ready = timezone.now()
            self.message_user(request, 'Fiber Ready')
        elif 'GPONE' in groups:
            if not prop.gear_ready:
                prop.gear_ready = timezone.now()
            self.message_user(request, 'Gear Ready For Pickup')
        elif 'FE' in groups:
            if not prop.gear_installed:
                prop.gear_installed = timezone.now()
            self.message_user(request, 'Gear Installed')
        elif 'CC' in groups:
            if not prop.cross_connect:
                prop.cross_connect = timezone.now()
            self.message_user(request, 'Cross-Connected')
        prop.save()
        url = reverse(
            'admin:geomap_property_changelist',
            current_app=self.admin_site.name,
        )
        return HttpResponseRedirect(url)

    def property_map(self, request, property_id):
        prop = self.get_object(request, property_id)

        if not prop.location:
            self.message_user(request, 'No coordinates for this property')
            url = reverse(
                'admin:geomap_property_change',
                args=[prop.pk],
                current_app=self.admin_site.name,
            )
            return HttpResponseRedirect(url)

        context = self.admin_site.each_context(request)

        context['properties'] = Property.objects.filter(~Q(pk=prop.pk))
        context['property'] = prop

        r_feeds = []
        for proper in Property.objects.filter(feeds__isnull=False):
            r_feeds += proper.get_links()
        context['r_feeds'] = r_feeds

        context['gpon_feeds'] = [proper.get_gpon_coord() for proper in Property.objects.filter(gpon_feed__isnull=False)]

        return TemplateResponse(
            request,
            'property_map.html',
            context,
        )

    def change_state(self, request, property_id, action):
        prop = self.get_object(request, property_id)
        if action == 'published':
            prop.set_unset_action(action)
        elif action in ['fiber_ready', 'mdf_ready', 'network_ready', 'gpon_ready']:
            if prop.published:
                prop.set_unset_action(action)
            else:
                self.message_user(request, 'Property needs to be Published')
        elif action == 'gear_installed':
            if prop.network_ready and prop.gpon_ready:
                if not prop.cross_connect:
                    prop.set_unset_action(action)
                else:
                    self.message_user(request, 'This Property was already cross-connected')
            else:
                self.message_user(request, 'The MDF Ready and Equipment Configured')
        elif action == 'cross_connect':
            if prop.gear_installed:
                if not prop.mr_cert:
                    prop.set_unset_action(action)
                else:
                    self.message_user(request, 'This Property was already certify')
            else:
                self.message_user(request, 'Gear needs to be installed')
        elif action == 'mr_cert':
            if prop.gear_installed:
                if not prop.done:
                    prop.set_unset_action(action)
                else:
                    self.message_user(request, 'This Property was already finished launched')
            else:
                self.message_user(request, 'Fiber needs to be cross-connected')
        elif action == 'done':
            if prop.mr_cert:
                if not prop.done:
                    prop.set_unset_action(action)
                else:
                    self.message_user(request, 'This Property was already finished launched')
            else:
                self.message_user(request, 'Property needs to be Certify')

        prop.save()

        url = reverse(
            'admin:geomap_property_change',
            args=[prop.pk],
            current_app=self.admin_site.name,
        )

        return HttpResponseRedirect(url)

    class Media:
        js = (
            "//cdnjs.cloudflare.com/ajax/libs/leaflet-polylinedecorator/1.1.0/leaflet.polylineDecorator.min.js",
        )
admin.site.register(Property, PropertyAdmin)