import os
from copy import copy

from kubernetes import client, config, watch
import slack


def _generate_progress_bar(position, max_value):
    if position is None:
        position = 0

    filled_squares = (100 / max_value * position) / 5

    filled_char = "⬛"
    empty_char = "⬜"
    return (filled_char * int(filled_squares)) + (
            empty_char * (20 - int(filled_squares))) + "\n"


class KubeLookout:
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

    def __init__(self, warning_image, progress_image, ok_image,
                 slack_key, slack_channel, cluster_name):
        super().__init__()
        self.warning_image = warning_image
        self.ok_image = ok_image
        self.progress_image = progress_image
        self.slack_client = None
        self.slack_key = slack_key
        self.slack_channel = slack_channel
        self.cluster_name = cluster_name
        self.rollouts = {}
        self.degraded = set()

    def _init_client(self):
        if "KUBERNETES_PORT" in os.environ:
            config.load_incluster_config()
        else:
            config.load_kube_config()
        api_client = client.api_client.ApiClient()
        self.core = client.ExtensionsV1beta1Api(api_client)

    def _send_slack_block(self, blocks, channel, message_id=None):
        if self.slack_client is None:
            self.slack_client = slack.WebClient(
                self.slack_key)
        if message_id is None:
            response = self.slack_client.chat_postMessage(channel=channel,
                                                          blocks=blocks)
            return response.data['ts'], response.data['channel']
        response = self.slack_client.chat_update(
            channel=channel,
            ts=message_id, blocks=blocks)
        return response.data['ts'], response.data['channel']

    def _handle_deployment_change(self, deployment):
        metadata = deployment.metadata
        deployment_key = f"{metadata.namespace}/{metadata.name}"

        if deployment_key not in self.rollouts and \
                deployment.status.updated_replicas is None:
            blocks = self._generate_deployment_rollout_block(deployment)
            resp = self._send_slack_block(blocks, self.slack_channel)
            self.rollouts[deployment_key] = resp

        elif deployment_key in self.rollouts:
            rollout_complete = (
                    deployment.status.updated_replicas ==
                    deployment.status.replicas ==
                    deployment.status.ready_replicas)
            blocks = self._generate_deployment_rollout_block(deployment,
                                                             rollout_complete)
            self.rollouts[deployment_key] = self._send_slack_block(
                channel=self.rollouts[deployment_key][1],
                message_id=self.rollouts[deployment_key][0], blocks=blocks)

            if rollout_complete:
                self.rollouts.pop(deployment_key)
        elif deployment.status.ready_replicas < deployment.spec.replicas:
            blocks = self._generate_deployment_degraded_block(deployment)
            self._send_slack_block(blocks, self.slack_channel)
            self.degraded.add(deployment_key)

        elif (deployment_key in self.degraded and
              deployment.status.ready_replicas
              >= deployment.spec.replicas):
            self.degraded.remove(deployment_key)
            blocks = self._generate_deployment_not_degraded_block(deployment)
            self._send_slack_block(blocks, self.slack_channel)

    def _handle_event(self, deployment):
        self._handle_deployment_change(deployment)

    def main_loop(self):
        while True:
            self._init_client()
            pods = self.core.list_deployment_for_all_namespaces(watch=False)
            resource_version = pods.metadata.resource_version
            stream = watch.Watch().stream(
                self.core.list_deployment_for_all_namespaces,
                resource_version=resource_version
            )
            print("Waiting for deployment events to come in..")
            for event in stream:
                deployment = event['object']
                obj = event["object"]
                code = obj.get("code")
                if code == 410:
                    print("Received HTTP 410, restarting..")
                    break
                self._handle_event(deployment)

    def _generate_deployment_rollout_block(self, deployment,
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
        message += _generate_progress_bar(
            deployment.status.updated_replicas, deployment.spec.replicas)

        block[0]['text']['text'] = header
        block[1]['text']['text'] = message
        block[1]['accessory']['image_url'] = self.progress_image
        if rollout_complete:
            block[1]['accessory'][
                'image_url'] = self.ok_image
        return block

    def _generate_deployment_degraded_block(self, deployment):

        block = copy(self.template)

        header = f"*{self.cluster_name} deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has become degraded.*"

        message = f"Deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has {deployment.status.ready_replicas} ready replicas " \
            f"when it should have {deployment.spec.replicas}.\n"

        message += _generate_progress_bar(deployment.status.ready_replicas,
                                          deployment.spec.replicas)

        block[0]['text']['text'] = header
        block[1]['text']['text'] = message
        block[1]['accessory'][
            'image_url'] = self.warning_image

        return block

    def _generate_deployment_not_degraded_block(self, deployment):
        block = copy(self.template)

        header = f"*{self.cluster_name} deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" is no longer in a degraded state.*"

        message = f"Deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has {deployment.status.ready_replicas} ready " \
            f"replicas out of " \
            f"{deployment.spec.replicas}.\n"

        message += _generate_progress_bar(deployment.status.ready_replicas,
                                          deployment.spec.replicas)

        block[0]['text']['text'] = header
        block[1]['text']['text'] = message
        block[1]['accessory'][
            'image_url'] = self.ok_image

        return block


if __name__ == "__main__":
    env_warning_image = os.environ.get(
        "WARNING_IMAGE",
        "https://upload.wikimedia.org/wikipedia/"
        "commons/thumb/6/6e/Dialog-warning.svg/"
        "200px-Dialog-warning.svg.png")
    env_progress_image = os.environ.get("PROGRESS_IMAGE",
                                        "https://i.gifer.com/80ZN.gif")
    env_ok_image = os.environ.get("OK_IMAGE",
                                  "https://upload.wikimedia.org/wikipedia/"
                                  "commons/thumb/f/fb/Yes_check.svg/"
                                  "200px-Yes_check.svg.png")
    env_slack_token = os.environ["SLACK_TOKEN"]
    env_slack_channel = os.environ.get("SLACK_CHANNEL", "#general")
    env_cluster_name = os.environ.get("CLUSTER_NAME", "Kubernetes Cluster")
    kube_deploy_watch = KubeLookout(env_warning_image,
                                    env_progress_image,
                                    env_ok_image, env_slack_token,
                                    env_slack_channel, env_cluster_name)

    kube_deploy_watch.main_loop()
