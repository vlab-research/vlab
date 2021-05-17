kubectl delete -f ../kube/facebot.yaml
docker build -t localhost:5000/facebot:registry .
docker push localhost:5000/facebot:registry
kubectl apply -f ../kube/facebot.yaml


