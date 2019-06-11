from copy import copy
import flowdock

from .receiver import Receiver


class FlowdockReceiver(Receiver):

    NAME = "flowdock"

    template = {
        "author": {
            "name": "KubeLookout",
        },
        "title": "Title",
        "external_thread_id": "Item-1",
        "thread": {
            "title": "thread-title",
            "body": "body-html",
            "external_url": "https://url-from-annotation.example.com",
            "status": {
                "value": "Deploying...",
                "color": "red",
            }
        }
    }

    def __init__(self, cluster_name, team, images, flowdock_token):
        super().__init__(cluster_name, team, images)
        self.flowdock_client = None
        self.flowdock_token = flowdock_token
        self.channel = "fake-not-used-yet-as-tied-to-token"

        print("configured flow-receiver for %s" % (self.team))

    def _send_message(self, data, new_resource, channel=None, message_id=None):
        # FIXME: channel not used here
        item_id = data.get('resource_uid')
        author = data.get('author')
        title = "deploy monitor"
        item = data.get("thread")

        if self.flowdock_client is None:
            self.flowdock_client = flowdock.connect(
                flow_token=self.flowdock_token)

        if message_id is None:
            # Send a new message
            response = self.flowdock_client.present(item_id, author=author,
                                                    title=title, body=item['body'], thread=item)
            # FIXME - this is not ideal
            return item_id, item_id

        # Update exiting message
        response = self.flowdock_client.present(item_id, author=author,
                                                title=title,
                                                body=item['body'],
                                                thread=item)

        # FIXME - this is not ideal
        return item_id, item_id

    def _generate_deployment_rollout_message(self, deployment,
                                             new_resource,
                                             rollout_complete=False):

        data = copy(self.template)

        message = ''
        if new_resource:
            message += f"<b>New</b> deployment started at {deployment.metadata.creation_timestamp}</br></br>"
        else:
            for container in deployment.spec.template.spec.containers:
                message += f"Container {container.name} has image " \
                    f"<b>{container.image}</b>"

            message += "<br>"
            message += f"{deployment.status.updated_replicas} replicas " \
                f"updated out of " \
                f"{deployment.spec.replicas}, {deployment.status.ready_replicas}" \
                f" ready.<br><br."

        replicas = f"{deployment.status.ready_replicas}/{deployment.spec.replicas}"

        header = f"[{replicas}] {self.cluster_name.upper()}: deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}"

        data["thread"]["title"] = header
        data["thread"]["body"] = message

        if rollout_complete:
            data["thread"]["status"]["value"] = 'DEPLOYED'
            data["thread"]["status"]["color"] = 'green'
        else:
            data["thread"]["status"]["value"] = 'DEPLOYING'
            data["thread"]["status"]["color"] = 'blue'

        data['resource_uid'] = deployment.metadata.uid

        return data

    def _generate_deployment_degraded_message(self, deployment):


        replicas = f"{deployment.status.ready_replicas}/{deployment.spec.replicas}"

        header = f"[{replicas}] {self.cluster_name.upper()}: deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}"

        message = f"Deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has {deployment.status.ready_replicas} ready replicas " \
            f"when it should have {deployment.spec.replicas}.<br>"

        data = copy(self.template)
        data["title"] = header
        data["thread"]["title"] = header
        data["thread"]["body"] = message

        data["thread"]["status"]["value"] = 'DEGRADED'
        data["thread"]["status"]["color"] = 'red'

        data['resource_uid'] = deployment.metadata.uid

        return data

    def _generate_deployment_not_degraded_message(self, deployment):

        replicas = f"{deployment.status.ready_replicas}/{deployment.spec.replicas}"

        header = f"[{replicas}] {self.cluster_name.upper()}: deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}"

        message = f"Deployment " \
            f"{deployment.metadata.namespace}/{deployment.metadata.name}" \
            f" has {deployment.status.ready_replicas} ready " \
            f"replicas out of " \
            f"{deployment.spec.replicas}.<br>"

        data = copy(self.template)
        data["title"] = header
        data["thread"]["title"] = header
        data["thread"]["body"] = message

        data["thread"]["status"]["value"] = 'DEPLOYED'
        data["thread"]["status"]["color"] = 'green'

        data['resource_uid'] = deployment.metadata.uid

        return data
