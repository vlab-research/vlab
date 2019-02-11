eval $(minikube docker-env)

# Secrets
kubectl delete secret gbv-bot-envs
kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube
docker build -t nandanrao/gbv-botserver:0.0.2 .
kubectl apply -f kube

# Port forwarding
sleep 5
kubectl port-forward $(kubectl get pods -l "app=gbv-botserver" -o jsonpath="{.items[0].metadata.name}") 3000:80
