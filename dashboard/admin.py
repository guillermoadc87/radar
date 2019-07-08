from django.contrib import admin
from .list_filters import MonthListFilter, YearListFilter
from .models import PropertySummary

# Register your models here.
@admin.register(PropertySummary)
class PropertySummaryAdmin(admin.ModelAdmin):
    list_filter = (MonthListFilter, YearListFilter)

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)

        response.context_data['filter_qs'] = list(self.filter_qs)
        print(self.total_qs)
        response.context_data['total_qs'] = dict(self.total_qs)

        return response