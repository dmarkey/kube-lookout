import os
from kubernetes import client, config


class Receiver(object):

    def __init__(self, warning_image, progress_image, ok_image, cluster_name):

        self.warning_image = warning_image
        self.ok_image = ok_image
        self.progress_image = progress_image

        self.cluster_name = cluster_name
        self.rollouts = {}
        self.degraded = set()

        self.channel = None

    def _init_client(self):
        if "KUBERNETES_PORT" in os.environ:
            config.load_incluster_config()
        else:
            config.load_kube_config()
        api_client = client.api_client.ApiClient()
        self.core = client.ExtensionsV1beta1Api(api_client)


    def _handle_deployment_change(self, deployment):
        metadata = deployment.metadata
        deployment_key = f"{metadata.namespace}/{metadata.name}"

        ready_replicas = 0

        if deployment.status.ready_replicas is not None:
            ready_replicas = deployment.status.ready_replicas

        if deployment_key not in self.rollouts and \
                deployment.status.updated_replicas is None:

            data = self._generate_deployment_rollout_message(deployment)
            resp = self._send_message(data)

            self.rollouts[deployment_key] = resp

        elif deployment_key in self.rollouts:
            rollout_complete = (
                    deployment.status.updated_replicas ==
                    deployment.status.replicas ==
                    ready_replicas)
            data = self._generate_deployment_rollout_message(deployment,
                                                             rollout_complete)

            self.rollouts[deployment_key] = self._send_message(
                message_id = self.rollouts[deployment_key][0], data=data)

            if rollout_complete:
                self.rollouts.pop(deployment_key)

        elif ready_replicas < deployment.spec.replicas:
            data = self._generate_deployment_degraded_message(deployment)
            self._send_message(data)
            self.degraded.add(deployment_key)

        elif (deployment_key in self.degraded and
              ready_replicas >= deployment.spec.replicas):
            self.degraded.remove(deployment_key)
            data = self._generate_deployment_not_degraded_message(deployment)
            self._send_message(data)

    def _handle_event(self, deployment):
        self._handle_deployment_change(deployment)
