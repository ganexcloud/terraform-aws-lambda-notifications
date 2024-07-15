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
    #elif 'Records' in event and len(event['Records']) > 0 and 'EventSource' in event['Records'][0] and event['Records'][0]['EventSource'] == 'aws:sns' and 'aws.codepipeline' not in event['Records'][0]['Sns']['Message'] and 'AlarmName' not in event['Records'][0]['Sns']['Message']:
    #    return 'sns'

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
            msteams_color = "good"
        elif state == 'STARTED':
            color = '00bbff'
            status = 'started'
            squadcast_status = "trigger"
            msteams_color = "default"
        elif state == 'FAILED':
            color = 'ff0000'
            status = 'failed'
            squadcast_status = "trigger"
            msteams_color = "attention"
        elif state == 'SUPERSEDED':
            color = '808080'
            status = 'superseded'
            squadcast_status = "resolve"
            msteams_color = "light"
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
                "description": f"**AWS Account:** {aws_account_id} \n**AWS Region:** {aws_region} \n**Pipeline:** {pipeline} \n**Status:** {status} \n**URL:** {pipeline_url} \n**Priority:** P5",
                "status": f"{squadcast_status}",
                "event_id": f"CodePipeline {pipeline} {status}"
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

        # Microsoft Teams
        elif messenger == 'msteams':
            message = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "$schema":"http://adaptivecards.io/schemas/adaptive-card.json",
                            "version": "1.4",
                            "msteams": {  
                                "width": "Full"  
                            },  
                            "body": [
                                {
                                    "type": "Container",
                                    "style": msteams_color,
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "size": "Large",
                                            "weight": "Bolder",
                                            "text": f"CodePipeline {pipeline} {status}",
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"AWS Account: {aws_account_id}\n\nAWS Region: {aws_region}\n\nPipeline: {pipeline}",
                                            "wrap": True,
                                        },
                                        {
                                            "type": "ActionSet",
                                            "actions": [
                                                {
                                                    "type": "Action.OpenUrl",
                                                    "title": "More Info",
                                                    "url": pipeline_url
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                ]
            }
            return message
        
    # CodeBuild
    elif 'Records' in event and len(event['Records']) > 0 and 'EventSource' in event['Records'][0] and 'aws.codebuild' in event['Records'][0]['Sns']['Message']:
        message = json.loads(event['Records'][0]['Sns']['Message'])
        aws_account_id = message.get('account', None)
        aws_region = message.get('region', None)
        event_time = message.get('time', None)
        project_name = message.get('detail', {}).get('project-name', None)
        status = message.get('detail', {}).get('build-status', None)
        codebuild_url = f'''https://{aws_region}.console.aws.amazon.com/codesuite/codebuild/pipelines/{project_name}/view?region={aws_region}'''
        color = '808080'
        blocks = list()
        footer = list()
        if status == 'SUCCEEDED':
            color = '00ff00'
            status = 'succeeded'
            squadcast_status = "resolve"
            msteams_color = "good"
        elif status == 'FAILED':
            color = 'ff0000'
            status = 'failed'
            squadcast_status = "trigger"
            msteams_color = "attention"
        elif status == 'IN_PROGRESS':
            color = '808080'
            status = 'in-progress'
            squadcast_status = "resolve"
            msteams_color = "default"
        elif status == 'STOPPED':
            color = 'ff0000'
            status = 'failed'
            squadcast_status = "trigger"
            msteams_color = "default"
        else:
            color = '000000'
            status = 'unknow'
            squadcast_status = "trigger"
            msteams_color = "default"

        # Slack
        if messenger == 'slack':
            message = {
                'attachments': [
                    {
                        "mrkdwn_in": ["text"],
                        'fallback': 'Pipeline Status',
                        'color': f"#{color}",
                        'author_icon': 'https://www.awsgeek.com/AWS-History/icons/AWS-CodeBuild.svg',
                        "text": f"Codebuild {project_name} {status} (<{codebuild_url}|Open>)"
                    }
                ]
            }
            return message

        # Squadcast
        elif messenger == 'squadcast':
            message = {
                "message": f"CodeBuild {project_name} {status}",
                "description": f"**AWS Account:** {aws_account_id} \n**AWS Region:** {aws_region} \n**Project:** {project_name} \n**Status:** {status} \n**URL:** {codebuild_url} \n**Priority:** P5",
                "status": f"{squadcast_status}",
                "event_id": f"CodeBuild {project_name} {status}"
            }
            return message

        # Discord
        elif messenger == 'discord':
            color = int(color, base=16)
            message = {
                'embeds': [
                    {
                        "title": f"CodeBuild {pipeline} {status}",
                        "description": f"[Open]({pipeline_url})",
                        "color": color
                    }
                ]
            }
            return message

        # Microsoft Teams
        elif messenger == 'msteams':
            message = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "$schema":"http://adaptivecards.io/schemas/adaptive-card.json",
                            "version": "1.4",
                            "msteams": {  
                                "width": "Full"  
                            },  
                            "body": [
                                {
                                    "type": "Container",
                                    "style": msteams_color,
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "size": "Large",
                                            "weight": "Bolder",
                                            "text": f"CodeBuild Summary {pipeline} {status}"
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"**AWS Account:** {aws_account_id} \n\n**AWS Region:** {aws_region} \n\n**Project:** {project_name} \n\n**Status:** {status} \n\n**Priority:** P5",
                                            "wrap": True,
                                        },
                                        {
                                            "type": "ActionSet",
                                            "actions": [
                                                {
                                                    "type": "Action.OpenUrl",
                                                    "title": "More Info",
                                                    "url": codebuild_url
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                ]
            }
            return message
        
    # ECS
    if 'Records' in event and len(event['Records']) > 0 and 'EventSource' in event['Records'][0] and 'aws.ecs' in event['Records'][0]['Sns']['Message']:
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
                         '• Region: ' + region + '\n' + \
                         '• Cluster: ' + detail['clusterArn'] + '\n' + \
                         '• Task Definition: ' + task_definition + '\n' + \
                         '• Last: ' + detail['lastStatus'] + ' ' + '\n' + \
                         '• Desired: ' + detail['desiredStatus'] + ' ' + '\n' + \
                         '• Priority: (P3)' + ' '
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

        def ecs_events_parser_title(detail_type, detail):
            if detail_type == 'ECS Container Instance State Change':
                result = "ECS Container Instance State Change"
                return result

            elif detail_type == 'ECS Deployment State Change':
                result = "ECS Deployment State Change"
                return result

            elif detail_type == 'ECS Service Action':
                result = "ECS Service Action"
                return result

            elif detail_type == 'ECS Task State Change':
                try:
                    reason = detail['stoppedReason']
                except Exception:
                    reason = "UNKNOWN"
                try:
                    group = detail['group']
                except Exception:
                    group = "UNKNOWN"
                result =  f"{reason} on {group}"
                return result

            else:
                result = f'Detail type "{detail_type}" unknown, see the original event on ECS to more informations.'
                return result

        message = json.loads(event['Records'][0]['Sns']['Message'])
        detail_type = message.get('detail-type')
        event_id = ecs_events_parser_title(detail_type, message.get('detail'))
        account = message.get('account')
        time = message.get('time')
        region = message.get('region')
        title = ecs_events_parser_title(detail_type, message.get('detail'))
        resources = []
        for resource in message.get('resources'):
            try:
                resources.append(resource.split(':')[5])
            except Exception:
                log.error('Error parsing the resource ARN: `{}`'.format(resource))
                resources.append(resource)
        detail = ecs_events_parser(detail_type, message.get('detail'))
        blocks = list()
        contexts = list()
        footer = list()

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

        # Squadcast
        elif messenger == 'squadcast':
            message = {
                "message": f'{title}',
                "description": f'{detail}',
               # "status": f"{squadcast_status}",
                "event_id": f'{title}'
            }
            return message
       
        # Microsoft Teams
        elif messenger == 'msteams':
            message = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "$schema":"http://adaptivecards.io/schemas/adaptive-card.json",
                            "version": "1.4",
                            "msteams": {  
                                "width": "Full"  
                            },  
                            "body": [
                                {
                                    "type": "Container",
                                    "style": "attention",
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "size": "Large",
                                            "weight": "Bolder",
                                            "text": title
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": detail,
                                            "wrap": True,
                                        }
                                    ]
                                }
                            ],
                        }
                    }
                ]
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
        alarm_url = "https://console.aws.amazon.com/cloudwatch/home?region=" + os.environ['AWS_REGION'] + "#alarmsV2:alarm/" + urllib.parse.quote(alarmName, safe='')
        if newState == "ALARM":
            color = "892621"
            squadcast_status = "trigger"
            msteams_color = "attention"
        elif newState == "OK":
            color = "00c575"
            squadcast_status = "resolve"
            msteams_color = "good"

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
                "event_id": alarmName
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

        # Microsoft Teams
        elif messenger == 'msteams':
            message = {
                "type": "message",
                "attachments": [
                    {
                        "contentType": "application/vnd.microsoft.card.adaptive",
                        "content": {
                            "type": "AdaptiveCard",
                            "$schema":"http://adaptivecards.io/schemas/adaptive-card.json",
                            "version": "1.4",
                            "body": [
                                {
                                    "type": "Container",
                                    "style": msteams_color,
                                    "items": [
                                        {
                                            "type": "TextBlock",
                                            "size": "Large",
                                            "weight": "Bolder",
                                            "text": alarmName,
                                        },
                                        {
                                            "type": "TextBlock",
                                            "text": f"**AWS Account:** {aws_account_id} \n\n **AWS Region:** {aws_region} \n\n **Description:** {alarmDescription} \n\n**State**: {newState}",
                                            "wrap": "true",
                                        },
                                        {
                                            "type": "ActionSet",
                                            "actions": [
                                                {
                                                    "type": "Action.OpenUrl",
                                                    "title": "More Info",
                                                    "url": alarm_url
                                                }
                                            ]
                                        }
                                    ]
                                }
                            ],
                        }
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
    if MESSENGER in ('slack', 'discord', 'squadcast', 'msteams'):
        message = handle_event(MESSENGER, event)
        response = post(WEBHOOK_URL, message)
        if response not in (200,204):
            log.error(
                "Error: received status `{}` using event `{}` and context `{}`".format(response, json.dumps(event, indent=4), context))
        return json.dumps({"code": response})

    else:
        raise ValueError(f'Not support messenger {MESSENGER}')
