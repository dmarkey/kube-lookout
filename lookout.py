import yaml
import os
import sys
import argparse

from kubernetes import watch, client, config

from receivers.slack_receiver import SlackReceiver
from receivers.flowdock_receiver import FlowdockReceiver


ANNOTATION_ENABLED = "kube-lookout/enabled"
ANNOTATION_TEAM = "kube-lookout/team"
ANNOTATION_RECEIVER = "kube-lookout/receiver"


#
# Define a specific yaml loader which substitutes environment
# vars.
#
class YamlEnvLoader(yaml.SafeLoader):
    def construct_yaml_str(self, node):
        return self.construct_scalar(node).format(**os.environ)


YamlEnvLoader.add_constructor(
    'tag:yaml.org,2002:str',
    YamlEnvLoader.construct_yaml_str)


def main_loop(receivers):

    if "KUBERNETES_PORT" in os.environ:
        config.load_incluster_config()
    else:
        config.load_kube_config()
    api_client = client.api_client.ApiClient()
    core = client.ExtensionsV1beta1Api(api_client)

    event_types = ['ADDED', 'MODIFIED']

    while True:
        pods = core.list_deployment_for_all_namespaces(watch=False)
        resource_version = pods.metadata.resource_version
        stream = watch.Watch().stream(core.list_deployment_for_all_namespaces,
                                      resource_version=resource_version)

        print("Waiting for deployment events to come in..")
        for event in stream:
            # Event type
            # ADDED | MODIFIED | DELETED
            event_type = event['type']
            deployment = event['object']

            # We only care about new/updated events (for now)
            if event_type not in event_types:
                continue

            # Parse out annotations
            annotations = deployment.metadata.annotations

            # Skip watching this deployment unless we've enabled it explicity
            if annotations.get(ANNOTATION_ENABLED) != "true":
                continue

            # Get team routing information from annotation
            annotation_team = annotations.get(ANNOTATION_TEAM)
            annotation_receiver = annotations.get(ANNOTATION_RECEIVER)

            print(f"got event for {deployment.metadata.namespace}/{deployment.metadata.name}")

            new_resource = True if event_type == 'ADDED' else False

            for receiver in receivers:
                receiver.handle_event(annotation_team,
                                      annotation_receiver,
                                      deployment,
                                      new_resource)


def get_images_from_config(image_config):
    warning_image = image_config.get("warn", os.environ.get("WARNING_IMAGE"))
    ok_image = image_config.get("ok", os.environ.get("OK_IMAGE"))
    progress_image = image_config.get("progress",
                                      os.environ.get("PROGRESS_IMAGE"))

    return {'ok': ok_image,
            'warning': warning_image,
            'progress': progress_image}


def format_constructor(loader, node):
    return loader.construct_scalar(node).format(**os.environ)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True,
                        help='path to configuration file')

    args = parser.parse_args()

    config_file = args.config

    if not os.path.exists(config_file):
        print("Config not found: %s" % (config_file))
        sys.exit(1)

    print("Using config: %s" % (config_file))

    with open(config_file, 'r') as ymlfile:
        yaml_loader = YamlEnvLoader(ymlfile)
        try:
            yaml_config = yaml_loader.get_single_data()
        finally:
            yaml_loader.dispose()

    cluster_name = yaml_config.get("cluster_name",
                                   os.environ.get("CLUSTER_NAME",
                                                  "Kubernetes Cluster"))

    images = get_images_from_config(yaml_config.get("images", {}))

    receivers = []

    slack_settings = yaml_config.get("receivers", {}).get("slack", {})
    flowdock_settings = yaml_config.get("receivers", {}).get("flowdock", {})

    for team, settings in slack_settings.items():
        receivers.append(SlackReceiver(cluster_name,
                                       team,
                                       images,
                                       settings.get("token"),
                                       settings.get("channel")))

    for team, settings in flowdock_settings.items():
        receivers.append(FlowdockReceiver(cluster_name,
                                          team,
                                          images,
                                          settings.get("token")))

    if not receivers:
        print("No valid receivers defined in config.yml")
        sys.exit(1)

    main_loop(receivers)
