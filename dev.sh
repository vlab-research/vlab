ktl delete -f kube
microk8s.docker build -t nandanrao/gbv-replybot:0.0.2 .
ktl apply -f kube
