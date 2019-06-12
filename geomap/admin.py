from django.utils import timezone
from django.contrib import admin
from .models import Property, Device, Interface, Statistics
from .views import PropertyListView
from django.urls import re_path, path
from django.utils.html import format_html
from django.urls import reverse
from django.shortcuts import render
from django.http import HttpResponseRedirect, StreamingHttpResponse, HttpResponse
from django.template.response import TemplateResponse
from django.db.models import Q
from .forms import PropertyForm, BUGraphForm, DeviceForm
from .list_filters import StatusListFilter
from django.contrib import messages
from wsgiref.util import FileWrapper
from io import BytesIO
from jinja2 import Environment, FileSystemLoader
from .nornir_api import get_graph_data
from .constants import AVAIL_INT_GRAPH

admin.site.site_header = 'HWC Launcher'
admin.site.site_title = "HWC Launcher"

class InterfaceInline(admin.TabularInline):
    model = Interface
    readonly_fields = ('name', 'connected')

    def get_queryset(self, request):
        qs = super(InterfaceInline, self).get_queryset(request)
        return qs.filter(connected__isnull=False)

    def has_add_permission(self, request):
        return False

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceForm
    inlines = (InterfaceInline,)
    search_fields = ('mgn', 'hostname', 'prop__name')
    list_display = ('hostname', 'model', 'mgn', 'account_actions')
    actions = ('bandwith_utilization',)
    ordering = ('-hostname',)
    list_max_show_all = 7000

    def avail_interfaces(self, obj):
        return None
    avail_interfaces.allow_tags = True
    avail_interfaces.short_description = 'Available Interfaces'

    def account_actions(self, obj):
        return format_html(
                '<a class="button" href="{}">Connect</a>&nbsp;',
                reverse('admin:connect_to_dev', args=[obj.pk]),
            )
    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id)

        if obj.model in AVAIL_INT_GRAPH:
            self.readonly_fields = ('avail_interfaces',)
            self.exclude = ()
            extra_context['data'] = get_graph_data(obj)
        else:
            self.readonly_fields = ()
            self.exclude = ('avail_interfaces',)
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('bu/', self.admin_site.admin_view(self.bu_graph), name='bu_graph'),
            re_path('connect/(?P<device_id>\d+)/', self.admin_site.admin_view(self.connect), name='connect_to_dev'),
        ]
        return my_urls + urls

    def get_graph_data(self, object_id):
        dev = Device.objects.get(pk=object_id)
        if dev.mgn:
            print(dev)
        return [{'id': '0', 'parent': '', 'name': 'Available Int'}, {'id': '1', 'parent': '0', 'name': 1}, {'id': '10', 'parent': '1', 'name': 'A9K-24X10GE-1G-TR'}, {'id': '100', 'parent': '10', 'name': 'Gi0/0/0/8', 'value': 1}, {'id': '101', 'parent': '10', 'name': 'Gi0/0/0/18', 'value': 1}, {'id': '102', 'parent': '10', 'name': 'Gi0/0/0/19', 'value': 1}, {'id': '103', 'parent': '10', 'name': 'Gi0/0/0/20', 'value': 1}, {'id': '104', 'parent': '10', 'name': 'Gi0/0/0/21', 'value': 1}, {'id': '105', 'parent': '10', 'name': 'Gi0/0/0/22', 'value': 1}, {'id': '106', 'parent': '10', 'name': 'Gi0/0/0/23', 'value': 1}, {'id': '2', 'parent': '0', 'name': 2}, {'id': '20', 'parent': '2', 'name': 'A9K-24X10GE-1G-TR'}, {'id': '200', 'parent': '20', 'name': 'Gi0/1/0/8', 'value': 1}, {'id': '201', 'parent': '20', 'name': 'Gi0/1/0/18', 'value': 1}, {'id': '202', 'parent': '20', 'name': 'Gi0/1/0/19', 'value': 1}, {'id': '203', 'parent': '20', 'name': 'Gi0/1/0/20', 'value': 1}, {'id': '204', 'parent': '20', 'name': 'Gi0/1/0/21', 'value': 1}, {'id': '205', 'parent': '20', 'name': 'Gi0/1/0/22', 'value': 1}, {'id': '206', 'parent': '20', 'name': 'Gi0/1/0/23', 'value': 1}]

    def bandwith_utilization(self, request, queryset):
        selected = request.POST.getlist(admin.ACTION_CHECKBOX_NAME)
        #print(selected)
        interfaces = []
        for device in queryset:
            for interface in device.interfaces.all():
                interfaces.append(interface)

        return HttpResponseRedirect(f'bu/?ids={",".join(selected)}')

    def bu_graph(self, request):
        context = {}
        if request.method == "POST":
            form = BUGraphForm(request.POST)

            if form.is_valid():
                start = form.cleaned_data['start']
                end = form.cleaned_data['end']
                interface_ids = form.cleaned_data['interfaces']

                print(start, end, interface_ids)

                stats = Statistics.objects.filter(interface__in=interface_ids, date__range=[start, end]).order_by('date')
                dates = stats.values_list('date', flat=True).distinct()
                print(stats)
                categories = [date.strftime('%m/%d/%Y') for date in dates]
                print(categories)

                series_maxin = []
                series_maxout = []
                for interface_id in interface_ids:
                    interface = Interface.objects.get(id=interface_id)
                    int_stats = stats.filter(interface=interface)
                    maxin = [stat.maxin for stat in int_stats]
                    maxout = [stat.maxout for stat in int_stats]
                    series_maxin.append({'name': f'{interface.name} - {interface.description}', 'data': maxin})
                    series_maxout.append({'name': f'{interface.name} - {interface.description}', 'data': maxout})

                context = {'categories': categories, 'series_maxin': series_maxin, 'series_maxout': series_maxout}
        else:
            form = BUGraphForm()

            devices_ids = request.GET.get('ids')
            devices_ids = devices_ids.split(',') if devices_ids else []
            print(devices_ids)
            devices = Device.objects.filter(id__in=devices_ids)
            #print(devices)
            interfaces = []
            for device in devices:
                for interface in device.interfaces.filter(statistics__isnull=False).distinct().order_by('name'):
                    interfaces.append((interface.pk, f'{device.hostname} - {interface.name} - {interface.description}'))
            form.fields['interfaces'].choices = interfaces
            context = {'form': form, 'interfaces': interfaces}

        return render(request, 'admin/bandwith_utilization.html', context={'form': form, **context})

    bandwith_utilization.short_description = "Bandwith Utilization"

    def connect(self, request, device_id):
        import os
        device = self.get_object(request, device_id)
        print(os.path.join(os.path.dirname(__file__), 'scripts'))
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'scripts'))
        env = Environment(loader=file_loader, trim_blocks=True, lstrip_blocks=True)
        template = env.get_template('connect.py').render(user=request.user.username, ip=device.mgn,)
        response = StreamingHttpResponse(template, content_type="application/py")
        response['Content-Disposition'] = f"attachment; filename={device.hostname}.py"
        return response

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    form = PropertyForm
    search_fields = ('name',)
    list_display = ('name', 'units', 'address', 'mr_cert', 'status', 'account_actions')
    list_filter = (StatusListFilter,)
    readonly_fields = ('map', 'inside_map', 'status')
    ordering = ('-mr_cert',)
    filter_horizontal = ('feeds',)
    fieldsets = (
        ('Circuit', {
            'fields': (
                'name',
                'address',
                'location',
                ('units', 'network', 'business_unit', 'type', 'contract',),
                'services',
                ('rf_unit', 'rf_coa', 'coa',),
            )
        }),
        ('Network', {
            'fields': (
                'map',
                'inside_map',
                'feeds',
                ('router', 'r_mgn'),
                ('switch', 's_mgn'),
            )
        }),
        ('GPON', {
            'fields': (
                ('gpon_feed', 'gpon_chassis', 'gpon_cards', 'gpon_ont'),
            )
        }),
        ('Subnets', {
            'fields': (
                ('ip_tv_coa', 'ip_tv', 'ip_voice', 'security'),
                ('ip_data', 'ip_data_bulk', 'ip_mgn', 'ip_mgn_ap'),
                ('nomadix_lan', 'nomadix_wan',),
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
        return obj.status
    status.allow_tags = True
    status.short_description = 'Status'

    def map(self, obj):
        return obj.map
    map.allow_tags = True
    map.short_description = 'OSP'

    def inside_map(self, obj):
        return None
    inside_map.allow_tags = True
    inside_map.short_description = 'ISP'

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

        r_feeds = []
        for proper in Property.objects.filter(feeds__isnull=False):
            r_feeds += proper.get_links()
        extra_context['r_feeds'] = r_feeds

        extra_context['gpon_feeds'] = [proper.get_gpon_coord() for proper in Property.objects.filter(gpon_feed__isnull=False)]

        extra_context['has_devices'] = True if Device.objects.filter(prop=prop) else False

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
            re_path('published/change/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'published', 'to_list': False}, name='publish_change'),
            re_path('fiber_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'fiber_ready'}, name='fiber_ready'),
            re_path('mdf_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'mdf_ready'}, name='mdf_ready'),
            re_path('network_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'network_ready'}, name='network_ready'),
            re_path('gpon_ready/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'gpon_ready'}, name='gpon_ready'),

            re_path('gear_installed/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'gear_installed'},
                    name='gear_installed'),
            re_path('cross_connect/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'cross_connect'}, name='cross_connect'),
            re_path('done/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'done'}, name='done'),
            re_path('done/change/(?P<property_id>\d+)', self.admin_site.admin_view(self.change_state),
                    {'action': 'done', 'to_list': False},name='done_change'),
            re_path('(?P<property_id>\d+)/change/connect', self.admin_site.admin_view(self.connect), name='connect'),
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
            'change_list_map.html',
            context,
        )

    def change_state(self, request, property_id, action, to_list=True):
        prop = self.get_object(request, property_id)
        groups = self.request.user.groups.all().values_list('name', flat=True)
        if action == 'published':
            if 'PM' in groups:
                prop.set_unset_action(self, request, action)
            else:
                self.message_user(request, 'You have to be a PM to Published a Project', level=messages.ERROR)
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
                    self.message_user(request, 'You have to be a PM to Complete a Project', level=messages.ERROR)
            else:
                self.message_user(request, 'Property needs to be Certify', level=messages.ERROR)

        prop.save()

        if to_list:
            url = reverse(
                'admin:geomap_property_changelist',
                current_app=self.admin_site.name,
            )
        else:
            url = reverse(
                'admin:geomap_property_change',
                args=(prop.id,),
                current_app=self.admin_site.name,
            )

        return HttpResponseRedirect(url)

    def connect(self, request, property_id):
        import os
        prop = self.get_object(request, property_id)
        print(os.path.join(os.path.dirname(__file__), 'scripts'))
        file_loader = FileSystemLoader(os.path.join(os.path.dirname(__file__), 'scripts'))
        env = Environment(loader=file_loader, trim_blocks=True, lstrip_blocks=True)
        template = env.get_template('connect.py').render(user=request.user.username, ip=prop.r_loop,)
        response = StreamingHttpResponse(template, content_type="application/py")
        response['Content-Disposition'] = "attachment; filename=connect.py"
        return response

    class Media:
        js = (
            "//cdnjs.cloudflare.com/ajax/libs/leaflet-polylinedecorator/1.1.0/leaflet.polylineDecorator.min.js",
        )
