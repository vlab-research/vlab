# Fly

Fly is a survey platform designed for longitudinal studies in poor network conditions and low powered devices.

## Deployment

Something like this:

``` shell
cd devops
./setup-kube.sh
helm install fly vlab -f values/production.yaml
```

## Development

Make sure you have KIND installed.

Then run:

``` shell
cd devops
./dev-cluster.sh
```
