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

kubectl wait --for=condition=Ready pod/gbv-cockroachdb-0 --timeout 5m

sleep 10

cat chatroach.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v19.2.3 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat migrate-1.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v19.2.3 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat migrate-2.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v19.2.3 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

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
