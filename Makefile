

build: ## Builds all of the go modules
	$(MAKE) -C dashboard-api build	&& mv dashboard-api/main .
