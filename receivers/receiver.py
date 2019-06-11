class Receiver(object):

    NAME = "receiver"

    def __init__(self, cluster_name, team, images):

        self.cluster_name = cluster_name
        self.team = team
        self.warning_image = images['warning']
        self.ok_image = images['ok']
        self.progress_image = images['progress']

        self.rollouts = {}

        self.channel = None

    def _handle_deployment_change(self, deployment, new_resource):
        metadata = deployment.metadata
        deployment_key = f"{metadata.namespace}/{metadata.name}"

        ready_replicas = int(deployment.status.ready_replicas) \
            if deployment.status.ready_replicas else 0

        rollout_complete = (
                deployment.status.updated_replicas ==
                deployment.status.replicas ==
                ready_replicas)

        if new_resource:
            data = self._generate_deployment_rollout_message(deployment, True)
            self.rollouts[deployment_key] = self._send_message(data, new_resource)

        elif rollout_complete:
            data = self._generate_deployment_rollout_message(deployment, False, True)

            self._send_message(
                data,
                new_resource,
                channel=self.rollouts[deployment_key][1],
                message_id=self.rollouts[deployment_key][0])

            self.rollouts.pop(deployment_key)

        elif ready_replicas < deployment.spec.replicas:
            data = self._generate_deployment_degraded_message(deployment)
            self._send_message(data, new_resource,
                channel=self.rollouts[deployment_key][1],
                message_id=self.rollouts[deployment_key][0])

    def _should_handle(self, team, receiver):
        return True if self.team == team and self.NAME == receiver \
            else False

    def handle_event(self, team, receiver, deployment, new_resource):
        if self._should_handle(team, receiver):
            print("Receiver '%s' handling event for team '%s'" % (receiver,
                                                                  team))

            self._handle_deployment_change(deployment, new_resource)
