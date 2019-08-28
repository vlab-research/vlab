eval $(minikube docker-env)

# Secrets
#kubectl delete secret gbv-bot-envs
#kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube/job.yaml

docker build -t localhost:32000/testrunner:registry testrunner/
docker push localhost:32000/testrunner:registry

kubectl apply -f kube/job.yaml

# kubelog gbv-facebot 0 --follow
