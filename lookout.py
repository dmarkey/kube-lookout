import configparser
import os
import sys
from copy import copy

from kubernetes import client, config, watch

from receivers.slack_receiver import SlackReceiver
from receivers.flowdock_receiver import FlowdockReceiver

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
            print(f"got event for {deployment.metadata.namespace}/{deployment.metadata.name}")
            receiver._handle_event(deployment)

if __name__ == "__main__":

    config = configparser.ConfigParser()
    config.read("config.ini")

    warning_image = config.get("default", "warning_image", fallback=os.environ.get("WARNING_IMAGE"))
    ok_image = config.get("default", "ok_image", fallback=os.environ.get("OK_IMAGE"))
    progress_image = config.get("default", "progress_image", fallback=os.environ.get("PROCESS_IMAGE"))
    cluster_name = config.get("default", "cluster_name", fallback=os.environ.get("CLUSTER_NAME", "Kubernetes Cluster"))

    if "receiver.slack" in config.sections():
        slack_token = config.get("receiver.slack", "token") or os.environ.get("SLACK_TOKEN")
        slack_channel = config.get("receiver.slack", "channel") or os.environ.get("SLACK_CHANNEL")

        receiver = SlackReceiver(warning_image,
                                progress_image,
                                ok_image, slack_token,
                                slack_channel, cluster_name)
    elif "receiver.flowdock" in config.sections():
        flowdock_token = config.get("receiver.flowdock", "token") or os.environ.get("FLOWDOCK_TOKEN")

        receiver = FlowdockReceiver(warning_image,
                                    progress_image,
                                    ok_image, flowdock_token,
                                    cluster_name)

    else:
        print("No receivers defined in config.ini")
        sys.exit(1)

    receiver._init_client()
    main_loop(receiver)
