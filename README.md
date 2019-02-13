# Replybot

Make sure you have a folder called keys at the root of this project, with a single file: "key.json" -- which is the google application credentials keys. 

Also make sure you have the .env file at the root of the project. This is currently the SAME for both botserver and replybot, so symlink one to the other!

## Setup local kubernetes

Make sure you install the following on your machine:

* [Virtual Box](https://www.virtualbox.org/wiki/Downloads)
* [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/)
* [minikube](https://kubernetes.io/docs/tasks/tools/install-minikube/)
* [helm](https://docs.helm.sh/using_helm/#installing-helm)

Now setup minikube and kubectl:

``` shell
minikube start
kubectl use-context minikube
```

Now, initialize helm in you minikube cluster and install Kafka using helm:

``` shell
helm --kube-context minikube init
helm repo add incubator http://storage.googleapis.com/kubernetes-charts-incubator
helm --kube-context minikube install --name spinaltap incubator/kafka
```

Run this in the shell you will be using

``` shell
eval $(minikube docker-env)
```

To reload or start an app (both botserver and replybot), inside the folder run:

NOTE: You will receive warnings the first time due to the fact that the script tries to delete the deployment, which will error if the deployment does not exist. That's ok. 

``` shell
./dev.sh
```

You should now see the pods running at: 

``` shell
kubectl get po
```

And you can get logs for an individual pod via: 

``` shell
kubectl logs [POD_NAME]
```

Or, handily, you can setup the following script (as kube-logs.sh, for example) and alias it to something useful on your computer: 

``` shell
NAME=$1
NUM=$2
kubectl logs $(kubectl get pods -l "app=${NAME}" -o jsonpath="{.items[${NUM}].metadata.name}")
```

Which you can then run:

``` shell
alias kubelog=kube-logs.sh
kubelog gbv-replybot 1
```
