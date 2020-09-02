#!/bin/sh

# App
helm delete scribble
docker build -t localhost:5000/scribble:registry .
docker push localhost:5000/scribble:registry
helm upgrade --install scribble chart/ -f values.yaml


