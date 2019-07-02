from slack import WebClient

slack_token = 'xoxp-447345546210-448398510663-672312122500-ce14e9a41f8ce384f9750b53e63c9182'
slack = WebClient(slack_token)

# Slack API

def create_channel_with(name):
    reponse = slack.channels_create(name=name)
    print(reponse)
    if not reponse['ok']:
        return None

    return reponse['channel']['id']

def upload_file_to_channel(channel, filepath):
    with open(filepath, 'rb') as file:
        slack.files_upload(channels=channel, file=file.read())

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
