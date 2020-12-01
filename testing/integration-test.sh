#!/bin/sh

######################
# env file for testing
######################

kubectl create secret generic gbv-bot-envs --from-env-file=./.test-env

######################
# install
######################

helm install gbv vlab -f values/dev.yaml
kubectl apply -f testing/facebot.yaml

######################
# create database
######################
sleep 20
kubectl wait --for=condition=Ready pod/gbv-cockroachdb-0 --timeout 20m
sleep 20

for f in `ls ./sql/* | sort -V`
do
cat $f | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public
done

######################
# wait for everything
######################

kubectl wait --for=condition=Ready pod/gbv-kafka-0
kubectl wait --for=condition=available \
        deployment/gbv-replybot \
        deployment/gbv-botserver \
        deployment/gbv-naughtybot-writer \
        deployment/gbv-linksniffer \
        deployment/gbv-scratchbot

sleep 20

######################
# run test
######################

kubectl apply -f testing/testrunner.yaml

kubectl wait --for=condition=complete job/gbv-testrunner --timeout 10m
kubectl logs -l app=gbv-testrunner

######################
# test success
######################

SUCCESS=$(kubectl get job gbv-testrunner -o jsonpath='{.status.succeeded}')
if [ -z "$SUCCESS" ]; then exit 1; fi
echo "Test Succesful!"
