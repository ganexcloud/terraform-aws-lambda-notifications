import os
import json
import logging
#import requests
import urllib
from botocore.vendored import requests

# ---------------------------------------------------------------------------------------------------------------------
# ENVIRONMENT VARIABLES
# ---------------------------------------------------------------------------------------------------------------------

LOG_LEVEL=(os.environ.get("LOG_LEVEL", "INFO").upper())
LOG_EVENTS = os.getenv('LOG_EVENTS', 'False').lower() in ('true', '1', 't', 'yes', 'y')
WEBHOOK_URL = os.environ['WEBHOOK_URL']
MESSENGER = os.environ['MESSENGER']

if WEBHOOK_URL == '':
    raise RuntimeError('The required env variable WEBHOOK_URL is not set or empty!')

if MESSENGER == '':
    raise RuntimeError('The required env variable MESSENGER is not set or empty!')

# ---------------------------------------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------------------------------------------------
log = logging.getLogger()
log.setLevel(LOG_LEVEL)

# Handler event
def handle_event(messenger, event: dict):
    # S3
    if 'Records' in event and len(event['Records']) > 0 and 'eventSource' in event['Records'][0] and event['Records'][0]['eventSource'] == 'aws:s3':
        return 's3'

    # SNS
    elif 'Records' in event and len(event['Records']) > 0 and 'EventSource' in event['Records'][0] and event['Records'][0]['EventSource'] == 'aws:sns' and 'aws.codepipeline' not in event['Records'][0]['Sns']['Message'] and 'AlarmName' not in event['Records'][0]['Sns']['Message']:
        return 'sns'

    # Codepipeline
    elif 'Records' in event and len(event['Records']) > 0 and 'EventSource' in event['Records'][0] and 'aws.codepipeline' in event['Records'][0]['Sns']['Message']:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        aws_account_id = message.get('account', None)
        aws_region = message.get('region', None)
        event_time = message.get('time', None)
        pipeline = message.get('detail', {}).get('pipeline', None)
        state = message.get('detail', {}).get('state', None)
        pipeline_url = f'''https://{aws_region}.console.aws.amazon.com/codesuite/codepipeline/pipelines/{pipeline}/view?region={aws_region}'''
        color = '808080'
        blocks = list()
        footer = list()
        if state == 'SUCCEEDED':
            color = '00ff00'
            status = 'succeeded'
            squadcast_status = "resolve"
        elif state == 'STARTED':
            color = '00bbff'
            status = 'started'
            squadcast_status = "trigger"
        elif state == 'FAILED':
            color = 'ff0000'
            status = 'failed'
            squadcast_status = "trigger"
        elif state == 'SUPERSEDED':
            color = '808080'
            status = 'superseded'
            squadcast_status = "resolve"
        else:
            color = '000000'

        # Slack
        if messenger == 'slack':
            message = {
                'attachments': [
                    {
                        "mrkdwn_in": ["text"],
                        'fallback': 'Pipeline Status',
                        'color': f"#{color}",
                        'author_icon': 'https://www.awsgeek.com/AWS-History/icons/AWS-CodePipeline.svg',
                        "text": f"CodePipeline {pipeline} {status} (<{pipeline_url}|Open>)"
                    }
                ]
            }
            return message

        # Squadcast
        elif messenger == 'squadcast':
            message = {
                "message": f"CodePipeline {pipeline} {status}",
                "description": f"**Pipeline:** {pipeline} \n**Status:** {status} \n**URL:** {pipeline_url} \n**Priority:** P5",
                "status": f"{squadcast_status}",
                "event_id": "6"
            }
            return message

        # Discord
        elif messenger == 'discord':
            color = int(color, base=16)
            message = {
                'embeds': [
                    {
                        "title": f"CodePipeline {pipeline} {status}",
                        "description": f"[Open]({pipeline_url})",
                        "color": color
                    }
                ]
            }
            return message

    # ECS
    elif 'source' in event and event['source'] == 'aws.ecs':
        def ecs_events_parser(detail_type, detail):
            if detail_type == 'ECS Container Instance State Change':
                result = f'*Instance ID:* ' + detail['ec2InstanceId'] + '\n' + \
                         '• Status: ' + detail['status']
                if 'statusReason' in detail:
                    result = result + '\n' + '• Reason: ' + detail['statusReason']
                return result

            if detail_type == 'ECS Deployment State Change':
                result = f'*Event Detail:*' + '\n' + \
                         '• ' + detail['eventType'] + ' - ' + detail['eventName'] + '\n' + \
                         '• Deployment: ' + detail['deploymentId'] + '\n' + \
                         '• Reason: ' + detail['reason']
                return result

            elif detail_type == 'ECS Service Action':
                result = f'*Event Detail:*' + '\n' + \
                         '• ' + detail['eventType'] + ' - ' + detail['eventName']
                if 'capacityProviderArns' in detail:
                    capacity_providers = ""
                    for capacity_provider in detail['capacityProviderArns']:
                        try:
                            capacity_providers = capacity_providers + capacity_provider.split(':')[5].split('/')[1] + ", "
                        except Exception:
                            log.error('Error parsing clusterArn: `{}`'.format(capacity_provider))
                            capacity_providers = capacity_providers + capacity_provider + ", "
                    if capacity_providers != "":
                        result = result + '\n' + '• Capacity Providers: ' + capacity_providers
                return result

            elif detail_type == 'ECS Task State Change':
                container_instance_id = "UNKNOWN"
                if 'containerInstanceArn' in detail:
                    try:
                        container_instance_id = detail['containerInstanceArn'].split(':')[5].split('/')[2]
                    except Exception:
                        log.error('Error parsing containerInstanceArn: `{}`'.format(detail['containerInstanceArn']))
                        container_instance_id = detail['containerInstanceArn']
                try:
                    task_definition = detail['taskDefinitionArn'].split(':')[5].split(
                        '/')[1] + ":" + detail['taskDefinitionArn'].split(':')[6]
                except Exception:
                    log.error('Error parsing taskDefinitionArn: `{}`'.format(detail['taskDefinitionArn']))
                    task_definition = detail['taskDefinitionArn']
                try:
                    task = detail['taskArn'].split(':')[5].split('/')[2]
                except Exception:
                    log.error('Error parsing taskArn: `{}`'.format(detail['taskArn']))
                    task = detail['taskArn']
                result = f'*Event Detail:* ' + '\n' + \
                         '• Task Definition: ' + task_definition + '\n' + \
                         '• Last: ' + detail['lastStatus'] + ' ' + '\n' + \
                         '• Desired: ' + detail['desiredStatus'] + ' '
                if container_instance_id != "UNKNOWN":
                    result = result + '\n' + '• Instance ID: ' + container_instance_id
                if detail['lastStatus'] == 'RUNNING':
                    if 'healthStatus' in detail:
                        result = result + '\n' + '• HealthStatus: ' + detail['healthStatus']
                if detail['lastStatus'] == 'STOPPED':
                    if 'stopCode' in detail:
                        result = result + '\n' + '• Stop Code: ' + detail['stopCode']
                    if 'stoppedReason' in detail:
                        result = result + '\n' + '• Stop Reason: ' + detail['stoppedReason']
                return result

            else:
                result = f'Detail type "{detail_type}" unknown, see the original event on ECS to more informations.'
                return result

        event_id = event.get('id')
        detail_type = event.get('detail-type')
        account = event.get('account')
        time = event.get('time')
        region = event.get('region')
        resources = []
        for resource in event['resources']:
            try:
                resources.append(resource.split(':')[5])
            except Exception:
                log.error('Error parsing the resource ARN: `{}`'.format(resource))
                resources.append(resource)
        detail = ecs_events_parser(detail_type, event.get('detail'))
        blocks = list()
        contexts = list()
        footer = list()
        title = f'*{detail_type}*'

        if messenger == 'slack':
            blocks.append(
                {
                    'type': 'section',
                    'text': {
                        'type': 'mrkdwn',
                        'text': title
                    }
                }
            )
            if resources:
                blocks.append(
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': "*Resources*:\n" + '\n'.join(resources)
                        }
                    }
                )
            if detail:
                blocks.append(
                    {
                        'type': 'section',
                        'text': {
                            'type': 'mrkdwn',
                            'text': detail
                        }
                    }
                )
            contexts.append({
                'type': 'mrkdwn',
                'text': f'Account: {account} Region: {region}'
            })
            contexts.append({
                'type': 'mrkdwn',
                'text': f'Time: {time} UTC Id: {event_id}'
            })
            blocks.append({
                'type': 'context',
                'elements': contexts
            })
            blocks.append({'type': 'divider'})
            return {'blocks': blocks}
        elif messenger == 'discord':
            contexts.append({
                'name': 'Resources',
                'value': '\n'.join(resources)
            })
            contexts.append({
                'name': 'Details',
                'value': detail
            })
            footer.append(
                {
                    'text': account
                }
            )
            blocks.append({
                'title': title,
                'fields': contexts,
                'footer': {
                    "text": f'Account: {account} | Region: {region}'
                }
            })
            return {'embeds': blocks}

        elif MESSENGER == 'squadcast':
            message = {
                "message": f"{title}",
                "description": f'{detail}',
               # "status": f"{squadcast_status}",
                "event_id": "6"
            }
            return message

    # CodeCommit
    elif 'Records' in event and len(event['Records']) > 0 and 'eventSource' in event['Records'][0] and event['Records'][0]['eventSource'] == 'aws:codecommit':
        return 'codecommit'

    # SES
    elif 'Records' in event and len(event['Records']) > 0 and 'eventSource' in event['Records'][0] and event['Records'][0]['eventSource'] == 'aws:ses':
        return 'ses'

    # CloudWatch
    elif 'Records' in event and len(event['Records']) > 0 and 'EventSource' in event['Records'][0] and 'AlarmName' in event['Records'][0]['Sns']['Message']:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        aws_account_id = message.get('AWSAccountId', None)
        aws_region = message.get('Region', None)
        subject = "AWS CloudWatch Notification";
        alarmName = message.get('AlarmName')
        metricName = message.get('Trigger', {}).get('MetricName', None)
        oldState = message.get('OldStateValue')
        newState = message.get('NewStateValue')
        alarmDescription = message.get('AlarmDescription')
        alarmReason = message.get('NewStateReason')
        trigger = message.get('Trigger')
        alarm_url = "https://console.aws.amazon.com/cloudwatch/home?region=" + urllib.parse.quote(aws_region, safe='') + "#alarm:alarmFilter=ANY;name=" + urllib.parse.quote(alarmName, safe='')
        if newState == "ALARM":
            color = "892621"
            squadcast_status = "trigger"
        elif newState == "OK":
            color = "00c575"
            squadcast_status = "resolve"

        # Slack
        if messenger == 'slack':
            message = {
                'attachments': [
                    {
                        'color': f'{color}',
                        "fields": [
                          { "value": alarmName, "short": "true" },
                          { "value": f"{alarmDescription} (<{alarm_url}|Open>)"}
                        ],
                    }
                ]
            }
            return message

        # Squadcast
        elif messenger == 'squadcast':
            message = {
                "message": alarmName,
                "description": f"{alarmDescription} \n**URL:** {alarm_url} \n**Message:** {message}\n**Priority:** P5",
                "status": f"{squadcast_status}",
                "event_id": "6"
            }
            return message

        # Discord
        elif messenger == 'discord':
            color = int(color, base=16)
            message = {
                'embeds': [
                    {
                        "title": alarmName,
                        "description": f"{alarmDescription} [Open]({alarm_url})",
                        "color": color
                    }
                ]
            }
            return message

# Post Webhook
def post(WEBHOOK_URL, message):
    log.debug(f'Sending message: {json.dumps(message, indent=4)}')
    headers = {'Content-type': 'application/json'}
    response = requests.post(WEBHOOK_URL, json.dumps(message), headers=headers)
    log.debug('Response: {}, message: {}'.format(response.status_code, response.text))
    return response.status_code

# Lambda handler
def lambda_handler(event, context):
    if LOG_EVENTS:
        log.info('Event logging enabled: `{}`'.format(json.dumps(event)))

    if MESSENGER in ('slack', 'discord', 'squadcast'):
        message = handle_event(MESSENGER, event)
        response = post(WEBHOOK_URL, message)
        if response not in (200,204):
            log.error(
                "Error: received status `{}` using event `{}` and context `{}`".format(response, event, context))
        return json.dumps({"code": response})

    else:
        raise ValueError(f'Not support messenger {MESSENGER}')
