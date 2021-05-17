#!/bin/sh

# eval $(minikube docker-env)

# Secrets
# kubectl delete secret gbv-replybot-keys
# kubectl delete secret gbv-bot-envs
# kubectl create secret generic gbv-replybot-keys --from-file=keys
# kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube-dev
# kubectl delete -f kube-dev/scratch-deployment.yaml
docker build -t localhost:5000/replybot:registry .
docker push localhost:5000/replybot:registry
kubectl apply -f kube-dev
# kubectl delete -f kube-dev/scratch-deployment.yaml


