from django.contrib import admin
from django.utils.html import format_html
from django.urls import re_path, path
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.core import management
from .models import Device

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    change_list_template = 'admin/reachability_tool/device/change_list.html'
    search_fields = ('name',)
    readonly_fields = ('ticket',)
    list_display = ('ticket', 'ip', 'state', 'target', 'account_actions')
    ordering = ('-target',)
    exclude = ('user',)

    def account_actions(self, obj):
        return format_html(
                '<a class="button" href="{}">Connect</a>&nbsp;<a class="button" href="https://jira.gethotwired.com/browse/{}">Jira</a>',
                reverse('admin:test_connect', args=[obj.pk]),
                obj.ticket,
            )
    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            re_path('connect/(?P<pk>\d+)$', self.admin_site.admin_view(self.connect), name='test_connect'),
            re_path('add_devices/$', self.admin_site.admin_view(self.add_devices), name='add_devices'),
        ]
        return my_urls + urls

    def connect(self, request, pk):
        management.call_command('connect', '--device=%s' % (pk,))

        url = reverse(
            'admin:reachability_tool_device_changelist',
            current_app=self.admin_site.name,
        )

        return HttpResponseRedirect(url)

    def add_devices(self, request):
        management.call_command('add_equipment')

        url = reverse(
            'admin:reachability_tool_device_changelist',
            current_app=self.admin_site.name,
        )

        return HttpResponseRedirect(url)

    def save_model(self, request, obj, form, change):
        #if not obj.pk:
        #    obj.user = request.user
        super().save_model(request, obj, form, change)