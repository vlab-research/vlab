#!/bin/bash

NS=$1
NAME=$2
SEARCH=$3

# get number of pods
NUM=$(kubectl -n $NS get pods -l "app.kubernetes.io/name=${NAME}" | wc -l)
NUM=$(expr $NUM - 2)

for i in $(eval echo {0..$NUM})
do
  kubectl -n $NS logs $(kubectl -n $NS get pods -l "app.kubernetes.io/name=${NAME}" -o jsonpath="{.items[${i}].metadata.name}") | grep "$SEARCH" -B 50 -A 50
done
