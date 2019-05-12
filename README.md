# kube-lookout
A utility to post changes to kubernetes deployments to Slack

## What does it do?

It listens to kubernetes deployment states and is interested when:

1. Any kubernetes deployment is rolling out a new version
2. If a kubernetes deployment is not healthy (Ready replicas is less than expected replicas)

It posts nice dynamic status updates for the above to slack

More to come
