import os
from django.utils import timezone
from django.core.management.base import BaseCommand
from reachability_tool.models import Device

states = {
    'alert': 1,
    'ok': 0
}

class Command(BaseCommand):
    args = '<foo bar ...>'
    help = 'our help string comes here'

    def add_arguments(self, parser):
        parser.add_argument('--device', type=int)

    def _connect(self, pk):
        devices = Device.objects.all()

        if pk:
            devices = devices.filter(pk=pk)

        for device in devices:
            passed = device.test_connectibity()
            if not passed:
                jira = JIRA('https://jira.gethotwired.com', basic_auth=('guillermo.diaz', 'Wktkm1987$') ,options={'verify': False})
                ticket = jira.issue(device.ticket)
                if issue.fields.status.name == 'Closed':
                	jira.transition_issue(ticket, transition='261')

    def handle(self, *args, **options):
        pk = None
        if options['device']:
            pk = options['device']
        self._connect(pk)
