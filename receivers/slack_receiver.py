from copy import copy
import utils
import slack

from .receiver import Receiver

class SlackReceiver(Receiver):
    template = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ""
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": ""
            },
            "accessory": {
                "type": "image",
                "image_url": "",
                "alt_text": "status image"
            }
        }
    ]

    def __init__(self, cluster_name, warning_image, progress_image, ok_image,
                 slack_key, channel):

        super().__init__(cluster_name, warning_image, progress_image, ok_image)

        self.slack_client = None
        self.slack_key = slack_key
        self.channel = channel

        print("configured slack-receiver for %s" % (self.channel))

    def _send_message(self, data, channel=None, message_id=None):
        if self.slack_client is None:
            self.slack_client = slack.WebClient(
                self.slack_key)

        if message_id is None:
            response = self.slack_client.chat_postMessage(channel=self.channel,
                                                          blocks=data)
        else:
            response = self.slack_client.chat_update(channel=channel,
                                                     ts=message_id,
                                                     blocks=data)

        return response.data['ts'], response.data['channel']

    def _generate_deployment_rollout_message(self, deployment,
                                             rollout_complete=False):

        block = copy(self.template)
        header = f"*{self.cluster_name} deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" is rolling out an update.*"
        message = ''
        for container in deployment.spec.template.spec.containers:
            message += f"Container {container.name} has image " \
                f"_ {container.image} _\n"
        message += "\n"
        message += f"{deployment.status.updated_replicas} replicas " \
            f"updated out of " \
            f"{deployment.spec.replicas}, {deployment.status.ready_replicas}" \
            f" ready.\n\n"
        message += utils.generate_progress_bar(
            deployment.status.updated_replicas, deployment.spec.replicas)

        block[0]['text']['text'] = header
        block[1]['text']['text'] = message
        block[1]['accessory']['image_url'] = self.progress_image
        if rollout_complete:
            block[1]['accessory'][
                'image_url'] = self.ok_image
        return block

    def _generate_deployment_degraded_message(self, deployment):

        block = copy(self.template)

        header = f"*{self.cluster_name} deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has become degraded.*"

        message = f"Deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has {deployment.status.ready_replicas} ready replicas " \
            f"when it should have {deployment.spec.replicas}.\n"

        message += utils.generate_progress_bar(deployment.status.ready_replicas,
                                          deployment.spec.replicas)

        block[0]['text']['text'] = header
        block[1]['text']['text'] = message
        block[1]['accessory'][
            'image_url'] = self.warning_image

        return block

    def _generate_deployment_not_degraded_message(self, deployment):
        block = copy(self.template)

        header = f"*{self.cluster_name} deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" is no longer in a degraded state.*"

        message = f"Deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has {deployment.status.ready_replicas} ready " \
            f"replicas out of " \
            f"{deployment.spec.replicas}.\n"

        message += utils.generate_progress_bar(deployment.status.ready_replicas,
                                          deployment.spec.replicas)

        block[0]['text']['text'] = header
        block[1]['text']['text'] = message
        block[1]['accessory'][
            'image_url'] = self.ok_image

        return block
