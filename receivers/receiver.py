class Receiver(object):

    NAME = "receiver"

    def __init__(self, cluster_name, team, images):

        self.cluster_name = cluster_name
        self.team = team
        self.warning_image = images['warning']
        self.ok_image = images['ok']
        self.progress_image = images['progress']

        self.rollouts = {}
        self.degraded = set()

        self.channel = None

    def _handle_deployment_change(self, deployment):
        metadata = deployment.metadata
        deployment_key = f"{metadata.namespace}/{metadata.name}"

        ready_replicas = 0
        if deployment.status.ready_replicas is not None:
            ready_replicas = deployment.status.ready_replicas

        rollout_complete = (
                deployment.status.updated_replicas ==
                deployment.status.replicas ==
                ready_replicas)

        if deployment_key not in self.rollouts and \
                deployment.status.updated_replicas is None:
            # This is a new deployment
            blocks = self._generate_deployment_rollout_message(deployment)
            print("AAA")
            self.rollouts[deployment_key] = self._send_message(
                channel=self.channel, data=blocks)
        elif ready_replicas < deployment.spec.replicas:
            # The deployment is degraded (less replicas than expected)
            print("BBB")

            blocks = self._generate_deployment_degraded_message(deployment)
            self._send_message(
                channel=self.rollouts[deployment_key][1],
                message_id=self.rollouts[deployment_key][0], data=blocks)

            self.degraded.add(deployment_key)

        elif (deployment_key in self.degraded and
              ready_replicas >= deployment.spec.replicas):
            # The deployment iwas degraded, but isn't any longer
            print("CC")
            self.degraded.remove(deployment_key)
            blocks = self._generate_deployment_not_degraded_message(deployment)

            self._send_message(
                channel=self.rollouts[deployment_key][1],
                message_id=self.rollouts[deployment_key][0], data=blocks)

        # FIXME: We can probably skip this
        if deployment_key in self.rollouts and rollout_complete:
            # The deployment is complete and OK
            print("DD")
            blocks = self._generate_deployment_rollout_message(deployment, rollout_complete)
            self._send_message(
                channel=self.rollouts[deployment_key][1],
                message_id=self.rollouts[deployment_key][0], data=blocks)

            self.rollouts.pop(deployment_key)

    def _should_handle(self, team, receiver):
        return True if self.team == team and self.NAME == receiver \
            else False

    def handle_event(self, team, receiver, deployment):
        if self._should_handle(team, receiver):
            print("Receiver '%s' handling event for team '%s'" % (receiver,
                                                                  team))

            self._handle_deployment_change(deployment)
