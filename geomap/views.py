from datetime import datetime
from django.views.generic import ListView
from .models import Property, Files
from django.http import HttpResponse, JsonResponse, Http404, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from .slack_api import file_download
import time
import json
from .helper_functions import open_ssh_session, send_command


class PropertyListView(ListView):
    """
        City detail view.
    """
    template_name = 'geomap.html'
    model = Property

def free_interface_command(request, ip):
    chan = open_ssh_session(ip)
    output = send_command(chan, 'sh int des | i admin')
    response = StreamingHttpResponse(output, content_type="application/txt")
    response['Content-Disposition'] = "attachment; filename=output.txt"
    return response

@csrf_exempt
def slack_commands(request):
    channel_id = request.POST.get('channel_id')
    try:
        prop = Property.objects.get(channel_id=channel_id)
    except Property.DoesNotExist:
        return HttpResponse('Could not find property')

    ts = int(request.META['HTTP_X_SLACK_REQUEST_TIMESTAMP'])
    print(ts)
    return JsonResponse({"text": "Detail Page: <https://c6c2cca4.ngrok.io/admin/geomap/property/%s/change/|%s> \n Router: %s" % (prop.pk, prop.name, prop.r_loop)})

@csrf_exempt
def save_image(request):
    if request.method == "GET":
        raise Http404("These are not the slackbots you're looking for.")
    time.sleep(4)

    try:
        # https://stackoverflow.com/questions/29780060/trying-to-parse-request-body-from-post-in-django
        event_data = json.loads(request.body.decode("utf-8"))
    except ValueError as e:  # https://stackoverflow.com/questions/4097461/python-valueerror-error-message
        return HttpResponse("")
    print(event_data)
    # Echo the URL verification challenge code
    if "challenge" in event_data:
        print(event_data["challenge"])
        return HttpResponse(event_data["challenge"], content_type="text/plain")

    channel_id = event_data['event']['channel_id']
    file_id = event_data['event']['file_id']
    print(file_id)
    try:
        prop = Property.objects.get(channel_id=channel_id)
    except Property.DoeDoesNotExist:
        print('prop not found')
        return HttpResponse('Could not find property')

    file_arg = file_download(channel_id, file_id)

    if file_arg:
        print('file saved!')
        files = Files()
        files.property = prop
        files.image.save(file_arg[0], file_arg[1])

        file_arg[1].close()

    return HttpResponse("Got it!")