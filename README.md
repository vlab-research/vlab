# Botserver

Running botserver (dev.sh) will port-forward the app to your localhost:3000. You will need to tunnel (ngrok) the externally if you want to test with a live Messenger app.

Also make sure you have the .env file at the root of the project. This is currently the SAME for both botserver and replybot, so symlink one to the other!

## Setup Live Messenger Testing

Go to the test application:
https://developers.facebook.com/apps/790352681363186/webhooks/

Under "Products" on the left sidebar, navigate to "Webhooks".

From the "Webhooks" page, you there is a button called "Edit Subscription" -- the callback url (assuming you ran `ngrok http 3000`)should be: `[HTTPS_NGROK_URL]/webhooks`

The "verify token" should be equal to the verify token in the .env file in the root of this project.

With that webhook setup, you should be able to message the bot. In your browser, navigate to:

https://m.me/testvirtuallab?ref=K41s40.001


## Setup new Messenger Application

This should only have to be done once for each new Messenger app!

1. Create a page

2. Create an application in developers/facebook

3. Enable Messenger

5. Create page access token

6. Connect bot to page events

7. Setup get_started payload
``` shell
curl -X POST -H "Content-type: application/json" -d '{ "get_started":{ "payload": "get_started"} }' "https://graph.facebook.com/v3.2/me/messenger_profile?access_token=${PAGE_ACCESS_TOKEN}"

```

8. Setup page username

9. Test via m.me link



## Setup local kubernetes

Make sure you install the following on your machine:

* minikube
* kubectl
* helm

Now setup minikube and kubectl:

``` shell
minikube start
kubectl --use-context minikube
```

Now, initialize helm in you minikube cluster and install Kafka using helm:

``` shell
helm --kube-context minikube init
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
