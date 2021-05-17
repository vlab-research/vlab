NAMESPACE=$1

kubectl -n $NAMESPACE create secret generic gbv-dumper-keys --from-file=../dumper/keys
kubectl -n $NAMESPACE create secret generic gbv-bot-envs --from-env-file=../replybot/.env
