#!/bin/sh

# App
helm delete dean
docker build -t localhost:5000/dean:registry .
docker push localhost:5000/dean:registry
helm upgrade --install dean chart/ -f values.yaml


