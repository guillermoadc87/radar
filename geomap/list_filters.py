from django.contrib import admin
from django.db.models import Q

class StatusListFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('New', 'New'),
            ('Published', 'Published'),
            ('Gear Configured', 'Gear Configured'),
            ('Fiber Ready', 'Fiber Ready'),
            ('MDF Ready', 'MDF Ready'),
            ('Gear Installed', 'Gear Installed'),
            ('Cross-Connected', 'Cross-Connected'),
            ('MR Certified', 'MR Certified'),
            ('Completed', 'Completed')
        ]

    def queryset(self, request, queryset):
        value = self.get_value(request)
        if value:
            if value == 'New':
                return queryset.filter(published__isnull=True)
            elif value == 'Published':
                return queryset.filter(published__isnull=False)
            elif value == 'Gear Configured':
                return queryset.filter(Q(network_ready__isnull=False) | Q(gpon_ready__isnull=False))
            elif value == 'Fiber Ready':
                return queryset.filter(fiber_ready__isnull=False)
            elif value == 'MDF Ready':
                return queryset.filter(mdf_ready__isnull=False)
            elif value == 'Gear Installed':
                return queryset.filter(gear_installed__isnull=False)
            elif value == 'Cross-Connected':
                return queryset.filter(cross_connect__isnull=False)
            elif value == 'MR Certified':
                return queryset.filter(mr_cert__isnull=False)
            elif value == 'Completed':
                return queryset.filter(done__isnull=False)
        return queryset

    def get_value(self, request):
        value = super().value()
        if value is None:
            groups = request.user.groups.all().values_list('name', flat=True)

            if 'CPM' in groups or 'FE' in groups:
                return 'Pending CXC'
            elif 'NETENG' in groups or 'GPONENG' in groups:
                return 'Pending Install'
            elif 'CXCENG' in groups:
                return 'Pending Done'

        return value