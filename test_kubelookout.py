from unittest.mock import Mock

from receivers.slack_receiver import SlackReceiver
from receivers.flowdock_receiver import FlowdockReceiver


def mock_images():
    return {'ok': 'ok.png',
            'warning': 'warning.png',
            'progress': 'progress.png'}

def test_slack_init():

    team = "teambobo"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    images = mock_images()

    klo = SlackReceiver(cluster_name, team, images, slack_key, slack_channel)

    assert klo.cluster_name == cluster_name
    assert klo.team == team
    assert klo.slack_key == slack_key
    assert klo.channel == slack_channel

    assert klo.ok_image == images['ok']
    assert klo.warning_image == images['warning']
    assert klo.progress_image == images['progress']


def test_send_slack_block():
    team = "teambobo"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    images = mock_images()

    klo = SlackReceiver(cluster_name, team, images, slack_key, slack_channel)

    mock_result = Mock()
    mock_result.data = {"ts": 123, "channel": "lala"}
    klo.slack_client = Mock()
    klo.slack_client.chat_postMessage = Mock(return_value=mock_result)
    result = klo._send_message({"the": "block"}, "#general")
    assert result[0] == 123
    assert result[1] == "lala"
    klo.slack_client.chat_postMessage.assert_called_once_with(
        blocks={'the': 'block'}, channel='#general')


def test_send_slack_block_channel_id():
    team = "teambobo"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    images = mock_images()

    klo = SlackReceiver(cluster_name, team, images, slack_key, slack_channel)

    mock_result = Mock()
    mock_result.data = {"ts": 123, "channel": "lala"}
    klo.slack_client = Mock()
    klo.slack_client.chat_update = Mock(return_value=mock_result)
    result = klo._send_message({"the": "block"}, "#general", 234)
    assert result[0] == 123
    assert result[1] == "lala"
    klo.slack_client.chat_update.assert_called_once_with(
        blocks={'the': 'block'}, channel='#general', ts=234)


def test_deployment_rollout():
    team = "teambobo"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    images = mock_images()

    klo = SlackReceiver(cluster_name, team, images, slack_key, slack_channel)
    klo._send_message = Mock(return_value=("1", "2"))

    deployment = Mock()

    deployment.metadata = Mock()

    deployment.metadata.namespace = "test"
    deployment.metadata.name = "test_deploy"
    deployment.status = Mock(ready_replicas=1)
    deployment.status.updated_replicas = None
    container1 = Mock(image="fooimage")
    container1.name = "foo"
    container2 = Mock(image="barmage")
    container2.name = "bar"
    deployment.spec.template.spec.containers = [container1, container2]
    deployment.spec.replicas = 2
    klo._handle_deployment_change(deployment, True)

    assert klo.rollouts == {'test/test_deploy': ('1', '2')}

    klo._send_message.assert_called_once_with(
        [{'type': 'section',
          'text': {'type': 'mrkdwn',
                   'text': '*bobo deployment test/test_deploy is rolling out an update.*'}},
         {'type': 'section',
          'text': {'type': 'mrkdwn',
                   'text': """Container foo has image _ fooimage _\nContainer bar has image _ barmage _\n\nNone replicas updated out of 2, 1 ready.\n\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜\n"""},
          'accessory': {
              'type': 'image',
              'image_url': 'progress.png',
              'alt_text': 'status image'}}]
        , 'slack_channel')

    deployment.status.updated_replicas = 2
    deployment.status.ready_replicas = 2
    deployment.status.replicas = 2
    klo._send_message = Mock(return_value=("1", "2"))
    klo._handle_deployment_change(deployment)
    klo._send_message.assert_called_once_with(data=[{'type': 'section',
                                                           'text': {
                                                               'type': 'mrkdwn',
                                                               'text': '*bobo deployment test/test_deploy is rolling out an update.*'}},
                                                          {'type': 'section',
                                                           'text': {
                                                               'type': 'mrkdwn',
                                                               'text': 'Container foo has image _ fooimage _\nContainer bar has image _ barmage _\n\n2 replicas updated out of 2, 2 ready.\n\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛\n'},
                                                           'accessory': {
                                                               'type': 'image',
                                                               'image_url': 'ok.png',
                                                               'alt_text': 'status image'}}],
                                                  channel='2', message_id='1')
    assert klo.rollouts == {}
    assert klo.degraded == set()


def test_nothing_happening():
    team = "teambobo"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    images = mock_images()

    klo = SlackReceiver(cluster_name, team, images, slack_key, slack_channel)
    klo._send_message = Mock(return_value=("1", "2"))

    deployment = Mock()

    deployment.metadata = Mock()

    deployment.metadata.namespace = "test"
    deployment.metadata.name = "test_deploy"
    deployment.status = Mock(ready_replicas=1)
    deployment.status.updated_replicas = 2
    deployment.status.ready_replicas = 2
    deployment.status.replicas = 2
    container1 = Mock(image="fooimage")
    container1.name = "foo"
    container2 = Mock(image="barmage")
    container2.name = "bar"
    deployment.spec.template.spec.containers = [container1, container2]
    deployment.spec.replicas = 2
    klo._handle_deployment_change(deployment)
    assert klo.rollouts == {}
    klo._send_message.assert_not_called()


def test_degrade():
    team = "teambobo"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    images = mock_images()

    klo = SlackReceiver(cluster_name, team, images, slack_key, slack_channel)

    klo._send_message = Mock(return_value=("1", "2"))

    deployment = Mock()

    deployment.metadata = Mock()

    deployment.metadata.namespace = "test"
    deployment.metadata.name = "test_deploy"
    deployment.status = Mock(ready_replicas=1)
    deployment.status.updated_replicas = 2
    deployment.status.ready_replicas = 0
    deployment.status.replicas = 2
    container1 = Mock(image="fooimage")
    container1.name = "foo"
    container2 = Mock(image="barmage")
    container2.name = "bar"
    deployment.spec.template.spec.containers = [container1, container2]
    deployment.spec.replicas = 2
    klo._handle_deployment_change(deployment)
    assert klo.rollouts == {}
    klo._send_message.assert_called_once_with([{'type': 'section',
                                                    'text': {'type': 'mrkdwn',
                                                             'text': '*bobo deployment test/test_deploy has become degraded.*'}},
                                                   {'type': 'section',
                                                    'text': {'type': 'mrkdwn',
                                                             'text': 'Deployment test/test_deploy has 0 ready replicas when it should have 2.\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜\n'},
                                                    'accessory': {
                                                        'type': 'image',
                                                        'image_url': 'warning.png',
                                                        'alt_text': 'status image'}}],
                                                  'slack_channel')

    assert klo.degraded == {"test/test_deploy"}
    klo._send_message = Mock(return_value=("1", "2"))
    deployment.status.ready_replicas = 2
    klo._handle_deployment_change(deployment)
    assert klo.degraded == set()
    klo._send_message.assert_called_once_with([{'type': 'section',
                                                    'text': {'type': 'mrkdwn',
                                                             'text': '*bobo deployment test/test_deploy is no longer in a degraded state.*'}},
                                                   {'type': 'section',
                                                    'text': {'type': 'mrkdwn',
                                                             'text': 'Deployment test/test_deploy has 2 ready replicas out of 2.\n⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛⬛\n'},
                                                    'accessory': {
                                                        'type': 'image',
                                                        'image_url': 'ok.png',
                                                        'alt_text': 'status image'}}],
                                                  'slack_channel')
