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

configuration file like so:

```yaml

reciever: slack|flowdock

default_token: some-token
default_channel: some-channel

flowdock: 
  channel: token1
  channel: token2
slack
  channel: token1
  channel: token1
```
