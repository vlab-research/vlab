eval $(minikube docker-env)

# Secrets
kubectl delete secret gbv-bot-envs
kubectl create secret generic gbv-bot-envs --from-env-file .env

# App
kubectl delete -f kube
docker build -t vlabresearch/facebot:0.0.1 .
kubectl apply -f kube
