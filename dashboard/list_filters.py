import calendar
from datetime import datetime
from django.contrib import admin
from django.db.models import Q
from django.db.models import Count, Sum
from .models import PropertySummary

class MonthListFilter(admin.SimpleListFilter):
    template = 'admin/filter.html'
    title = 'Month'
    parameter_name = 'month'

    def lookups(self, request, model_admin):
        self.model_admin = model_admin
        return [
            (month_number, month_name)
            for month_number, month_name in enumerate(calendar.month_name)
            if month_number > 0
        ]

    def queryset(self, request, queryset):
        month = self.get_value(request)
        year = request.GET.get('year') if request.GET.get('year') else datetime.now().year
        print(month, year, 'month')
        if month:
            queryset = queryset.values('market').annotate(
                total_published=Count('id', filter=Q(published__month=month) & Q(published__year=year)),
                total_certified=Count('id', filter=Q(mr_cert__month=month) & Q(mr_cert__year=year)),
                total_units=Sum('units', filter=Q(mr_cert__month=month) & Q(mr_cert__year=year)))

        self.model_admin.filter_qs = queryset
        self.model_admin.total_qs = queryset.aggregate(
                        total_published=Count('id', filter=Q(published__month=month) & Q(published__year=year)),
                        total_certified=Count('id', filter=Q(mr_cert__month=month) & Q(mr_cert__year=year)),
                        total_units=Sum('units', filter=Q(mr_cert__month=month) & Q(mr_cert__year=year)))
        return queryset

    def get_value(self, request):
        value = super().value()
        if value is None:
            value = datetime.now().month
        return value

class YearListFilter(admin.SimpleListFilter):
    template = 'admin/filter.html'
    title = 'Year'
    parameter_name = 'year'

    def lookups(self, request, model_admin):
        self.model_admin = model_admin
        years = list(PropertySummary.objects.values_list('mr_cert__year', flat=True).distinct())
        return [(year, year) for year in years if year is not None]

    def queryset(self, request, queryset):
        year = self.get_value(request)
        month = request.GET.get('month') if request.GET.get('month') else datetime.now().month
        print(month, year, 'year')
        if year:
            queryset = queryset.values('market').annotate(
                total_published=Count('id', filter=Q(published__month=month) & Q(published__year=year)),
                total_certified=Count('id', filter=Q(mr_cert__month=month) & Q(mr_cert__year=year)),
                total_units=Sum('units', filter=Q(mr_cert__month=month) & Q(mr_cert__year=year)))
        self.model_admin.filter_qs = queryset
        return queryset

    def get_value(self, request):
        value = super().value()
        if value is None:
            value = datetime.now().year
        return value