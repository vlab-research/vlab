# App
kubectl delete -f kube-dev
docker build -t localhost:5000/gbv-dashboard:registry .
docker push localhost:5000/gbv-dashboard:registry
kubectl apply -f kube-dev

# Port forwarding
sleep 8
kubectl port-forward $(kubectl get pods -l "app=gbv-dashboard" -o jsonpath="{.items[0].metadata.name}") 4000:3000
