#!/bin/sh

# App
kubectl delete -f kube-dev
docker build -t localhost:5000/replybot:registry .
docker push localhost:5000/replybot:registry
kubectl apply -f kube-dev


