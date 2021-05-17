#!/bin/sh

# App
helm delete dinersclub
docker build -t localhost:5000/dinersclub:registry .
docker push localhost:5000/dinersclub:registry
helm upgrade --install dinersclub chart/ -f values.yaml
