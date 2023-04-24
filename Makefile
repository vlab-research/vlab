

build: ## Builds all of the go modules
	$(MAKE) -C api build
	$(MAKE) -C inference build
