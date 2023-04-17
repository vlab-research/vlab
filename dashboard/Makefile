
.PHONY: certs
certs: ## Used to generate the certs for the development
	@mkdir -p tmp/certs
	@mkcert -install
	@mkcert -cert-file tmp/certs/cert.pem -key-file tmp/certs/key.pem localhost
