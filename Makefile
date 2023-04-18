

build: ## Builds all of the go modules
	$(MAKE) -C dashboard-api build
	$(MAKE) -C inference build
