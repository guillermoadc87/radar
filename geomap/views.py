import json
import asyncio
from django.views.generic import ListView
from django.http import HttpResponseRedirect, StreamingHttpResponse, HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from .models import Property
from .slack_api import upload_file_to_channel
from .constants import ISP_TOPOLOGY_PATH

loop = asyncio.get_event_loop()

class PropertyListView(ListView):
    """
        City detail view.
    """
    template_name = 'geomap.html'
    model = Property

@csrf_exempt
def slack_commands(request):
    if request.method == "POST":
        command = request.POST.get('command')
        text = request.POST.get('text')
        channel_id = request.POST.get('channel_id')
        if command == '/info':
            try:
                prop = Property.objects.get(channel_id=channel_id)
                if not text:
                    string = f'Name: {prop.name}\nAddress: {prop.address}'
                    return HttpResponse(json.dumps({"text": string}), content_type="application/json")
                elif text == 'isp':
                    loop.run_in_executor(None, send_topology_img, [prop, channel_id])
                    return HttpResponse(json.dumps({"text": 'File being uploaded...'}), content_type="application/json")
            except:
                return HttpResponse('Could not find the property')
    return HttpResponse('Command not suppoted')

def send_topology_img(args):
    prop = args[0]
    channel_id = args[1]

    prop.build_graph()

    upload_file_to_channel(channel_id, ISP_TOPOLOGY_PATH)

@csrf_exempt
def slack_events(request):
    if request.method == "POST":
        print(request.body)
        body_unicode = request.body.decode('utf-8')
        body = json.loads(body_unicode)
        challenge = body.get('challenge')
        if challenge:
            return HttpResponse(challenge)
    return HttpResponse('Incorrect Method')
