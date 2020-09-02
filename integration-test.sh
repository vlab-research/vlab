#!/bin/sh

######################
# setup cluster
######################

kind create cluster --name test --wait 5m
kubectl config use-context kind-test

######################
# env file for testing
######################

kubectl create secret generic gbv-bot-envs --from-env-file=./testing/.test-env

######################
# install
######################

helm install gbv vlab -f values/test.yaml
kubectl apply -f testing/facebot.yaml

######################
# create database
######################

sleep 20
kubectl wait --for=condition=Ready pod/gbv-cockroachdb-0 --timeout 20m
sleep 20

cat ./sql/chatroach.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat ./sql/migrate-1.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat ./sql/migrate-2.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat ./sql/migrate-3.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat ./sql/migrate-4.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

cat ./sql/migrate-5.sql | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:v20.1.4 --restart=Never --command -- ./cockroach sql --insecure --host gbv-cockroachdb-public

######################
# wait for everything
######################

kubectl wait --for=condition=Ready pod/gbv-kafka-0 --timeout 5m
kubectl wait --for=condition=available \
        deployment/gbv-replybot \
        deployment/gbv-botserver \
        deployment/gbv-linksniffer \
        deployment/scribble \
        --timeout 5m


######################
# run test
######################

sleep 120

kubectl apply -f testing/testrunner.yaml

kubectl wait --for=condition=complete job/gbv-testrunner --timeout 10m
kubectl logs -l app=gbv-testrunner

######################
# test success
######################

SUCCESS=$(kubectl get job gbv-testrunner -o jsonpath='{.status.succeeded}')
if [ -z "$SUCCESS" ]; then exit 1; fi
echo "Test Succesful!"
