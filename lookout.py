import os
from copy import copy

from kubernetes import client, config, watch

from receivers.slack_receiver import SlackReceiver

def main_loop(receiver):
    while True:
        pods = receiver.core.list_deployment_for_all_namespaces(watch=False)
        resource_version = pods.metadata.resource_version
        stream = watch.Watch().stream(
            receiver.core.list_deployment_for_all_namespaces,
                resource_version=resource_version
            )
        print("Waiting for deployment events to come in..")
        for event in stream:
            deployment = event['object']
            receiver._handle_event(deployment)

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

   
    receiver = SlackReceiver(env_warning_image,
                                    env_progress_image,
                                    env_ok_image, env_slack_token,
                                    env_slack_channel, env_cluster_name)

    receiver._init_client()
    main_loop(receiver)
