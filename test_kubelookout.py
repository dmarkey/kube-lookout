from unittest.mock import Mock
import pytest

from lookout import KubeLookout


def test__init():
    warning_image = "warning.png"
    ok_image = "ok.png"
    progress_image = "progress.png"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    klo = KubeLookout(warning_image, progress_image, ok_image,
                      slack_key, slack_channel, cluster_name)

    assert klo.slack_channel == slack_channel
    assert klo.ok_image == ok_image
    assert klo.warning_image == warning_image
    assert klo.progress_image == progress_image
    assert klo.slack_key == slack_key
    assert klo.cluster_name == cluster_name


def test_send_slack_block():
    warning_image = "warning.png"
    ok_image = "ok.png"
    progress_image = "progress.png"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    klo = KubeLookout(warning_image, progress_image, ok_image,
                      slack_key, slack_channel, cluster_name)

    mock_result = Mock()
    mock_result.data = {"ts": 123, "channel": "lala"}
    klo.slack_client = Mock()
    klo.slack_client.chat_postMessage = Mock(return_value=mock_result)
    result = klo._send_slack_block({"the": "block"}, "#general")
    assert result[0] == 123
    assert result[1] == "lala"
    klo.slack_client.chat_postMessage.assert_called_once_with(
        blocks={'the': 'block'}, channel='#general')


def test_send_slack_block_channel_id():
    warning_image = "warning.png"
    ok_image = "ok.png"
    progress_image = "progress.png"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    klo = KubeLookout(warning_image, progress_image, ok_image,
                      slack_key, slack_channel, cluster_name)

    mock_result = Mock()
    mock_result.data = {"ts": 123, "channel": "lala"}
    klo.slack_client = Mock()
    klo.slack_client.chat_update = Mock(return_value=mock_result)
    result = klo._send_slack_block({"the": "block"}, "#general", 234)
    assert result[0] == 123
    assert result[1] == "lala"
    klo.slack_client.chat_update.assert_called_once_with(
        blocks={'the': 'block'}, channel='#general', ts=234)


def test_deployment_rollout():
    warning_image = "warning.png"
    ok_image = "ok.png"
    progress_image = "progress.png"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    klo = KubeLookout(warning_image, progress_image, ok_image,
                      slack_key, slack_channel, cluster_name)
    klo._send_slack_block = Mock(return_value=("1", "2"))

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
    klo._handle_deployment_change(deployment)

    assert klo.rollouts == {'test/test_deploy': ('1', '2')}
    klo._send_slack_block.assert_called_once_with(
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
    klo._send_slack_block = Mock(return_value=("1", "2"))
    klo._handle_deployment_change(deployment)
    klo._send_slack_block.assert_called_once_with(blocks=[{'type': 'section',
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
    warning_image = "warning.png"
    ok_image = "ok.png"
    progress_image = "progress.png"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    klo = KubeLookout(warning_image, progress_image, ok_image,
                      slack_key, slack_channel, cluster_name)
    klo._send_slack_block = Mock(return_value=("1", "2"))

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
    klo._send_slack_block.assert_not_called()


def test_degrade():
    warning_image = "warning.png"
    ok_image = "ok.png"
    progress_image = "progress.png"
    slack_key = "slack_key"
    slack_channel = "slack_channel"
    cluster_name = "bobo"
    klo = KubeLookout(warning_image, progress_image, ok_image,
                      slack_key, slack_channel, cluster_name)
    klo._send_slack_block = Mock(return_value=("1", "2"))

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
    klo._send_slack_block.assert_called_once_with([{'type': 'section',
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
    klo._send_slack_block = Mock(return_value=("1", "2"))
    deployment.status.ready_replicas = 2
    klo._handle_deployment_change(deployment)
    assert klo.degraded == set()
    klo._send_slack_block.assert_called_once_with([{'type': 'section',
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


def _klo():
    klo = KubeLookout("warning.png", "progress.png", "ok.png",
                      "slack_key", "slack_channel", "bobo")
    klo._send_slack_block = Mock(return_value=("1", "2"))
    return klo


def _deployment(spec_replicas, updated_replicas=None, ready_replicas=None,
                replicas=None):
    deployment = Mock()
    deployment.metadata.namespace = "citi"
    deployment.metadata.name = "dbapi2"
    deployment.spec.replicas = spec_replicas
    deployment.status = Mock(updated_replicas=updated_replicas,
                             ready_replicas=ready_replicas,
                             replicas=replicas)
    container = Mock(image="dbapi2:v9.375.0")
    container.name = "dbapi2"
    deployment.spec.template.spec.containers = [container]
    return deployment


def test_image_change_on_zero_replica_deployment_is_ignored():
    klo = _klo()

    klo._handle_deployment_change(_deployment(spec_replicas=0))

    klo._send_slack_block.assert_not_called()
    assert klo.rollouts == {}
    assert klo.degraded == set()


def test_scaling_to_zero_mid_rollout_forgets_the_rollout():
    klo = _klo()
    klo._handle_deployment_change(_deployment(spec_replicas=2,
                                              ready_replicas=2, replicas=2))
    assert klo.rollouts == {"citi/dbapi2": ("1", "2")}
    klo._send_slack_block.reset_mock()

    klo._handle_deployment_change(_deployment(spec_replicas=0))

    klo._send_slack_block.assert_not_called()
    assert klo.rollouts == {}


def test_scaling_degraded_deployment_to_zero_clears_degraded():
    klo = _klo()
    klo._handle_deployment_change(_deployment(spec_replicas=2,
                                              updated_replicas=2,
                                              ready_replicas=1, replicas=2))
    assert klo.degraded == {"citi/dbapi2"}
    klo._send_slack_block.reset_mock()

    klo._handle_deployment_change(_deployment(spec_replicas=0))

    klo._send_slack_block.assert_not_called()
    assert klo.degraded == set()


def test_main_loop_keeps_watching_after_a_failing_event(monkeypatch):
    import lookout

    class StopLoop(Exception):
        pass

    klo = _klo()
    klo.core = Mock()
    init_calls = []

    def init_client():
        init_calls.append(1)
        if len(init_calls) > 1:
            raise StopLoop

    klo._init_client = init_client
    bad = _deployment(spec_replicas=2)
    good = _deployment(spec_replicas=3)
    handled = []

    def handle_event(deployment):
        if deployment is bad:
            raise ValueError("boom")
        handled.append(deployment)

    klo._handle_event = handle_event
    watcher = Mock()
    watcher.stream.return_value = iter([{"object": bad}, {"object": good}])
    monkeypatch.setattr(lookout.watch, "Watch", Mock(return_value=watcher))

    with pytest.raises(StopLoop):
        klo.main_loop()

    assert handled == [good]
