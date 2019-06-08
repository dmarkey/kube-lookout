## Add comment deployment attrs to message

- VCS link if available 
- GIT COMMIT if available

## Add per-deploymoment enable/disable annotation:

```
kube-lookout.com/enable-notification: [true|false]
```
## Add multiple channel support per deployment:

```
kube-lookout.com/channel: [channel-name]
```

## Cleanup flowdock threading

It's not threading correctly yet (should edit existing thread0

## Envars are useful, make them work with the config

Environment vars work really well wiht k8s, but this moves toward a config.

We could allow envars to be specified inside the config and take them from the env.

That way the config can be committed,  but envvars for secrets (tokens etc) can still be used
