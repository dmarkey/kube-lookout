import configparser
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
            print(deployment)
            receiver._handle_event(deployment)

if __name__ == "__main__":

    config = configparser.ConfigParser()
    config.read("config.ini")
    
    warning_image = config.get("default", "warning_image", fallback=os.environ.get("WARNING_IMAGE"))
    ok_image = config.get("default", "ok_image", fallback=os.environ.get("OK_IMAGE"))
    progress_image = config.get("default", "progress_image", fallback=os.environ.get("PROCESS_IMAGE"))
    cluster_name = config.get("default", "cluster_name", fallback=os.environ.get("CLUSTER_NAME", "Kubernetes Cluster"))

    slack_token = config.get("receiver.slack", "token", fallback=os.environ["SLACK_TOKEN"])
    slack_channel = config.get("receiver.slack", "channel", fallback=os.environ["SLACK_CHANNEL"])

    receiver = SlackReceiver(warning_image,
                             progress_image,
                             ok_image, slack_token,
                             slack_channel, cluster_name)

    receiver._init_client()
    main_loop(receiver)
