from jira import JIRA
from django.core.management.base import BaseCommand
from reachability_tool.models import Device

states = {
    'alert': 1,
    'ok': 0
}

class Command(BaseCommand):
    args = '<foo bar ...>'
    help = 'our help string comes here'

    def _add_equipment(self):
        jira = JIRA('https://jira.gethotwired.com', basic_auth=('guillermo.diaz', 'Wktkm1987$'),
                    options={'verify': False})
        query = jira.search_issues(r"issuetype='Equipment Provision' AND status=Closed AND updated>=startOfDay('0') AND 'Equipment Management IP' is not NULL")
        for ticket in query:
            mgn_ip = ticket.fields.customfield_13034
            reporter = ticket.fields.reporter.name
            device, created = Device.objects.get_or_create(ticket=ticket.key, ip=mgn_ip, reporter=reporter)

    def handle(self, *args, **options):
        self._add_equipment()
