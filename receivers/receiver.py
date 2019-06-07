class Receiver(object):

    def _handle_deployment_change(deployment):
        print("Not impl in base Receiver")

    def _handle_event(self, deployment):
        self._handle_deployment_change(deployment)
