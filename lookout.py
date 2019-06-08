import yaml
import os
import sys
import argparse

from kubernetes import watch, client, config

from receivers.slack_receiver import SlackReceiver
from receivers.flowdock_receiver import FlowdockReceiver


def main_loop(receivers):

    if "KUBERNETES_PORT" in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    api_client = client.api_client.ApiClient()
    core = client.ExtensionsV1beta1Api(api_client)

    while True:
        pods = core.list_deployment_for_all_namespaces(watch=False)
        resource_version = pods.metadata.resource_version
        stream = watch.Watch().stream(core.list_deployment_for_all_namespaces,
                                      resource_version=resource_version
                                      )

        print("Waiting for deployment events to come in..")
        for event in stream:
            deployment = event['object']
            print(f"got event for {deployment.metadata.namespace}/{deployment.metadata.name}")

            for receiver in receivers:
                receiver._handle_event(deployment)

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, help='path to configuration file')
    args = parser.parse_args()

    config_file = args.config

    if not os.path.exists(config_file):
        print("Config not found: %s" % (config_file))
        sys.exit(1)

    print("Using config: %s" % (config_file))
    with open(config_file, 'r') as ymlfile:
        yaml_config = yaml.load(ymlfile)

    images = yaml_config.get("images", {})
    warning_image = images.get("warn", os.environ.get("WARNING_IMAGE")) 
    ok_image = images.get("ok", os.environ.get("OK_IMAGE"))
    progress_image = images.get("progress", os.environ.get("PROGRESS_IMAGE"))

    cluster_name = yaml_config.get("cluster_name", os.environ.get("CLUSTER_NAME", "Kubernetes Cluster"))

    receivers = []

    slack_settings = yaml_config.get("receivers", {}).get("slack", {})
    flowdock_settings = yaml_config.get("receivers", {}).get("flowdock", {})

    for team, settings in slack_settings.items():
        receivers.append(SlackReceiver(cluster_name,
                                       warning_image,
                                       progress_image,
                                       ok_image,
                                       settings.get("token"),
                                       settings.get("channel")))

    for team, settings in flowdock_settings.items():
        receivers.append(FlowdockReceiver(cluster_name,
                                          warning_image,
                                          progress_image,
                                          ok_image,
                                          settings.get("token")))

    if not receivers:
        print("No valid receivers defined in config.yml")
        sys.exit(1)

    main_loop(receivers)
