#!/bin/sh

eval $(minikube docker-env)

# Secrets
kubectl delete secret gbv-replybot-keys
kubectl delete secret gbv-bot-envs
kubectl create secret generic gbv-replybot-keys --from-file=keys
kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube
docker build -t vlabresearch/gbv-replybot:0.0.14 .
kubectl apply -f kube
