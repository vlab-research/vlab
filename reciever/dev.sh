eval $(minikube docker-env)

# Secrets
#kubectl delete secret gbv-bot-envs
#kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f ../kube

docker build -t localhost:32000/facebot:registry .
docker push localhost:32000/facebot:registry

kubectl apply -f ../kube/deployment.yaml
kubectl apply -f ../kube/broker.yaml
kubectl apply -f ../kube/service.yaml

# kubelog gbv-facebot 0 --follow
