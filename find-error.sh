#!/bin/bash

NAME=$1
SEARCH=$2

# get number of pods
NUM=$(kubectl get pods -l "app.kubernetes.io/name=${NAME}" | wc -l)
NUM=$(expr $NUM - 2)

for i in $(eval echo {0..$NUM})
do
  kubectl logs $(kubectl get pods -l "app.kubernetes.io/name=${NAME}" -o jsonpath="{.items[${i}].metadata.name}") | grep "$SEARCH" -B 15 -A 10
done
