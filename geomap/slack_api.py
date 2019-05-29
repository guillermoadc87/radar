from slackclient import SlackClient
from io import BytesIO
from django.core.files import File
import requests
import shutil
import os
from django.conf import settings
import asyncio

slack_signing_secret = 'b1fd5ddedbee3ad289c8d4d79dd62c04'
slack_token = 'xoxp-447345546210-448398510663-499194031059-7d3af4d2865dbbbd7fd918f735c7ba2d'
slack = SlackClient(slack_token)

# Slack API

def create_channel_with(name):
    reponse = slack.api_call('channels.create', name=name)
    print(reponse)
    if not reponse['ok']:
        return None

    return reponse['channel']['id']

def invite_user(user, channel_id):
    if user.profile.slack_id:
        reponse = slack.api_call('channels.invite', channel=channel_id, user=user.profile.slack_id)
    #else:
    #    reponse = slack.api_call('users.admin.invite',
    #                             email=user.email,
    #                             first_name=user.first_name,
    #                             last_name=user.last_name,
    #                             channels=[channel_id])
        if not reponse['ok']:
            return False

    return True

def send_message(channel_id, text):
    reponse = slack.api_call('chat.postMessage', channel=channel_id, text=text)
    print(reponse)
    if not reponse['ok']:
        return False
    return True

async def file_download(channel_id, file_id):
    response = slack.api_call('files.list', channel=channel_id)
    print(response)
    file = [file for file in response['files'] if file.get('id') == file_id]
    print(file)
    if not file:
        print('could not found file')
        return None
    print('found file')

    url_private = file[0]['url_private']
    filename = file[0]['name']
    file_path = os.path.join(settings.MEDIA_ROOT, filename)
    headers = {'Authorization': 'Bearer %s' % (slack_token,)}

    r = requests.get(url_private, headers=headers)
    print('file downloaded')
    if r.status_code == 200:
        mfile = BytesIO()
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                mfile.write(chunk)
        #shutil.copyfileobj(r.raw, mfile)
        print('file returned')
        return (filename, File(mfile))
    return None