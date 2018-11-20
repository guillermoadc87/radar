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
from .list_filters import StatusListFilter
from django.contrib import messages

admin.site.site_header = 'HWC Launcher'
admin.site.site_title = "HWC Launcher"

class PropertyAdmin(admin.ModelAdmin):
    form = PropertyForm
    search_fields = ('name',)
    list_display = ('name', 'units', 'address', 'mr_cert', 'status', 'account_actions')
    list_filter = (StatusListFilter,)
    readonly_fields = ('map', 'status')
    ordering = ('-mr_cert',)
    filter_horizontal = ('feeds',)
    fieldsets = (
        ('Circuit', {
            'fields': (
                'name',
                'address',
                'location',
                'map',
                ('units', 'business_unit', 'type',),
                ('rf_unit', 'rf_coa', 'coa',),
            )
        }),
        ('Network', {
            'fields': (
                'feeds',
                ('router', 'r_loop'),
                ('switch', 's_loop'),
            )
        }),
        ('GPON', {
            'fields': (
                ('gpon_feed', 'gpon_chassis', 'gpon_cards'),
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

    def status(self, obj):
        return obj.get_status
    status.allow_tags = True
    status.short_description = 'Status'

    def map(self, obj):
        return obj.map
    map.allow_tags = True
    map.short_description = 'Map'

    def account_actions(self, obj):
        groups = self.request.user.groups.all().values_list('name', flat=True)

        if 'CPM' in groups:
            button = format_html(
                '<a class="button" href="{}">Fiber Ready</a>&nbsp;',
                '<a class="button" href="{}">MDF Ready</a>',
                reverse('admin:fiber_ready', args=[obj.pk]),
                reverse('admin:mdf_ready', args=[obj.pk]),
            )
        elif 'NETENG' in groups:
            button = format_html(
                '<a class="button" href="{}">Configured</a>&nbsp;',
                reverse('admin:network_ready', args=[obj.pk]),
            )
        elif 'GPONENG' in groups:
            button = format_html(
                '<a class="button" href="{}">Configured</a>&nbsp;',
                reverse('admin:gpon_ready', args=[obj.pk]),
            )
        elif 'FE' in groups:
            button = format_html(
                '<a class="button" href="{}">Installed</a>&nbsp;',
                reverse('admin:gear_installed', args=[obj.pk]),
            )
        elif 'CXCENG' in groups:
            button = format_html(
                '<a class="button" href="{}">Cross-Connected</a>&nbsp;',
                reverse('admin:set_date', args=[obj.pk]),
            )
        elif 'PM' in groups:
            button = format_html(
                '<a class="button" href="{}">Publish</a>&nbsp;'
                '<a class="button" href="{}">Completed</a>',
                reverse('admin:publish', args=[obj.pk]),
                reverse('admin:done', args=[obj.pk]),
            )
        else:
            button = 'None'
        return button
    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}

        prop = self.get_object(request, object_id)

        extra_context['properties'] = Property.objects.filter(~Q(pk=prop.pk))
        extra_context['property'] = prop
        print(prop.location)
        r_feeds = []
        for proper in Property.objects.filter(feeds__isnull=False):
            r_feeds += proper.get_links()
        extra_context['r_feeds'] = r_feeds

        extra_context['gpon_feeds'] = [proper.get_gpon_coord() for proper in Property.objects.filter(gpon_feed__isnull=False)]

        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('map/', self.admin_site.admin_view(self.property_map), name='property_list'),
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
            return qs.filter(Q(neteng=request.user) | Q(gponeng=request.user) | Q(cpm=request.user) | Q(fe=request.user) | Q(cxceng=request.user) | Q(pm=request.user))

    def property_map(self, request):
        #prop = self.get_object(request, property_id)

        context = self.admin_site.each_context(request)

        context['properties'] = Property.objects.all()
        #context['property'] = prop
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
        groups = self.request.user.groups.all().values_list('name', flat=True)
        if action == 'published':
            if 'PM' in groups:
                prop.set_unset_action(self, request, action)
            else:
                self.message_user(request, 'You have to be a PM to Published the project', level=messages.ERROR)
        elif action in ['fiber_ready', 'mdf_ready', 'network_ready', 'gpon_ready']:
            if prop.published:
                prop.set_unset_action(self, request, action)
            else:
                self.message_user(request, 'Property needs to be Published', level=messages.ERROR)
        elif action == 'gear_installed':
            if prop.network_ready and prop.gpon_ready:
                if not prop.cross_connect:
                    prop.set_unset_action(self, request, action)
                else:
                    self.message_user(request, 'This Property was already cross-connected', level=messages.ERROR)
            else:
                self.message_user(request, 'The MDF Ready and Equipment Configured', level=messages.ERROR)
        elif action == 'cross_connect':
            if prop.gear_installed:
                if not prop.mr_cert:
                    prop.set_unset_action(self, request, action)
                else:
                    self.message_user(request, 'This Property was already certify', level=messages.ERROR)
            else:
                self.message_user(request, 'Gear needs to be installed', level=messages.ERROR)
        elif action == 'done':
            if prop.cross_connect:
                if 'PM' in groups:
                    prop.set_unset_action(self, request, action)
                else:
                    self.message_user(request, 'You have to be a PM to Complete the project', level=messages.ERROR)
            else:
                self.message_user(request, 'Property needs to be Certify', level=messages.ERROR)

        prop.save()

        url = reverse(
            'admin:geomap_property_changelist',
            current_app=self.admin_site.name,
        )

        return HttpResponseRedirect(url)

    class Media:
        js = (
            "//cdnjs.cloudflare.com/ajax/libs/leaflet-polylinedecorator/1.1.0/leaflet.polylineDecorator.min.js",
        )
admin.site.register(Property, PropertyAdmin)