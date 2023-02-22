default: help

help: ## Show help for each of the Makefile recipes
	@fgrep -h "##" $(MAKEFILE_LIST) \
	 	| fgrep -v fgrep \
		| fgrep -v internal | sed -e 's/\\$$//' | sed -e 's/##//'

# A bit of a Hack in order to force cleanup
# after stopping or exiting
start-dev: ## Sets up local development environment
	 @bash -c "trap 'trap - SIGINT SIGTERM ERR; \
		 $(MAKE) stop; \
		 exit 1' \
		 SIGINT SIGTERM ERR; \
		 $(MAKE) start"

# A bit of a Hack in order to force cleanup
# after stopping or exiting
test: ## Runs tests
	 @bash -c "trap 'trap - SIGINT SIGTERM ERR; \
		 $(MAKE) stop; \
		 exit 1' \
		 SIGINT SIGTERM ERR; \
		 $(MAKE) test-internal"

stop: ## Stops and cleans up all containers
	@echo "\n>>> STOPPING DANGLING CONTAINERS <<<\n"
	@docker compose \
		-f docker-compose-common.yaml  \
		-f docker-compose-dev.yaml down \
		--remove-orphans
	@docker compose \
		-f docker-compose-common.yaml  \
		-f docker-compose-test.yaml down \
		--remove-orphans

start: stop ## Starts local containers
	@echo "\n>>> STARTING API IN DEV MODE <<<\n"
	@docker compose \
		-f docker-compose-common.yaml \
		-f docker-compose-dev.yaml up \
		--build

go-test: ## Runs the go tests 
	@go test ./... -v

test-internal: stop
	@echo "\n>>> SETTING UP API <<<\n"
	@docker compose \
		-f docker-compose-common.yaml \
		-f docker-compose-test.yaml \
		build api
	@echo "\n>>> RUNNING TEST CASES <<<\n"
	@docker compose \
		-f docker-compose-common.yaml \
		-f docker-compose-test.yaml \
		run api

