ktl delete -f kube
microk8s.docker build -t nandanrao/gbv-botserver:0.0.2 .
ktl apply -f kube
sleep 4
ktl port-forward $(ktl get pods -l "app=gbv-botserver" -o jsonpath="{.items[0].metadata.name}") 3000:80
