# Manually:

# Run for static IP:
# gcloud --project $PROJECT compute addresses create $CLUSTER_NAME-ip --region europe-west1


# PROJECT=toixotoixo
# CLUSTER_NAME=toixo-cluster
STATIC_IP=35.190.195.176

# # gcloud container clusters create my-regional-cluster --num-nodes 2 --region europe-west1 \
# # --node-locations europe-west1-b,europe-west1-c

# gcloud --project $PROJECT container clusters get-credentials --region europe-west1 $CLUSTER_NAME


kubectl create namespace routing

# # Install nginx-ingress
helm install -n routing nginx-ingress stable/nginx-ingress --set rbac.create=true --set controller.service.loadBalancerIP=$STATIC_IP

## Install cert-manager
kubectl apply --validate=false -f https://raw.githubusercontent.com/jetstack/cert-manager/v0.13.0/deploy/manifests/00-crds.yaml

# kubectl create namespace cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install -n routing cert-manager \
  --version v0.13.0 \
  jetstack/cert-manager

# KEEL
helm repo add keel-charts https://charts.keel.sh
helm repo update
helm upgrade --install keel --namespace=kube-system keel-charts/keel -f keel.yaml

# # Create cluster-issuer
kubectl create -f cm-issuer.yaml

# SSD
kubectl create -f ssd-storage.yaml
