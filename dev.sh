eval $(minikube docker-env)

# Secrets
kubectl delete secret gbv-bot-envs
kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube-dev
docker build -t localhost:32000/botserver:registry .
docker push localhost:32000/botserver:registry
kubectl apply -f kube-dev

# Port forwarding
sleep 5
kubectl port-forward $(kubectl get pods -l "app=gbv-botserver" -o jsonpath="{.items[0].metadata.name}") 3000:80
