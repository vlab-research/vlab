# FIRST SET UP KUBECTL TO POINT TO CLUSTER:

# SSD
# kubectl create -f ssd-storage.yaml

# Namespaces
kubectl create namespace cert-manager
kubectl create namespace routing
kubectl create namespace monitoring

# # Install nginx-ingress
helm install -n routing nginx-ingress stable/nginx-ingress --set rbac.create=true

## Install cert-manager
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install \
     cert-manager jetstack/cert-manager \
     --namespace cert-manager \
     --create-namespace \
     --version v1.3.0 \
     --set installCRDs=true

# wait for it to be ready
sleep 20

# Create cluster-issuer
kubectl create -f cm-issuer.yaml

# Create Prometheus Operator
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install --namespace monitoring prometheus prometheus-community/kube-prometheus-stack -f prometheus/values.yaml

# Create zookeeper operator and kafka operator
helm install zookeeper-operator banzaicloud-stable/zookeeper-operator

kubectl create --validate=false -f https://github.com/banzaicloud/kafka-operator/releases/download/v0.15.1/kafka-operator.crds.yaml
helm install kafka-operator banzaicloud-stable/kafka-operator

# wait for kafka-operator to be ready and make kafka/zk cluster
sleep 20
kubectl apply -f ./kafka-operator/prod

# wait for cluster and install exporter 
# TODO: bring this up to date with the latest chart version which
# now lives in the kafka_exporter repo: 
# https://github.com/danielqsj/kafka_exporter
sleep 30
helm install kafka-exporter kafka-exporter -f ./kafka-operator/exporter-values.yaml
