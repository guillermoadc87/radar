from slackclient import SlackClient

slack_token = 'xoxp-447345546210-448398510663-649203714324-bc6711c0078cdd89206e306ffd405cfb'
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
