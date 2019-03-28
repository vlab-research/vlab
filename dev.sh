eval $(minikube docker-env)

# Secrets
kubectl delete secret gbv-bot-envs
kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube
docker build -t vlabresearch/gbv-dashboard:0.0.1 .
kubectl apply -f kube

# Port forwarding
sleep 5
kubectl port-forward $(kubectl get pods -l "app=gbv-dashboard" -o jsonpath="{.items[0].metadata.name}") 4000:80