from django.contrib import admin
from django.db.models import Q

class StatusListFilter(admin.SimpleListFilter):
    title = 'Status'
    parameter_name = 'status'

    def lookups(self, request, model_admin):
        return [
            ('Pending Equipment', 'Pending Equipment'),
            ('Pending Fiber', 'Pending Fiber'),
            ('Pending MDF', 'Pending MDF'),
            ('Pending Install', 'Pending Install'),
            ('Pending CXC', 'Pending CXC'),
            ('Pending MR Cert', 'Pending MR Cert'),
            ('Done', 'Done')
        ]

    def queryset(self, request, queryset):
        value = self.get_value(request)
        if value:
            if value == 'Pending Equipment':
                return queryset.filter(Q(network_ready__isnull=True) | Q(gpon_ready__isnull=True))
            elif value == 'Pending Fiber':
                return queryset.filter(fiber_ready__isnull=True)
            elif value == 'Pending MDF':
                return queryset.filter(mdf_ready__isnull=True)
            elif value == 'Pending Install':
                print('Pending Install')
                return queryset.filter(gear_installed__isnull=True)
            elif value == 'Pending CXC':
                return queryset.filter(cross_connect__isnull=True)
            elif value == 'Pending MR Cert':
                return queryset.filter(mr_cert__isnull=True)
            elif value == 'Pending Done':
                return queryset.filter(done__isnull=True)

        return queryset

    def get_value(self, request):
        print('asdasdasdasd')
        value = super().value()
        if value is None:
            groups = request.user.groups.all().values_list('name', flat=True)

            if 'CPM' in groups or 'FE' in groups:
                return 'Pending CXC'
            elif 'NETENG' in groups or 'GPONENG' in groups:
                return 'Pending Install'
            elif 'CXCENG' in groups:
                return 'Pending MR Cert'

        return value