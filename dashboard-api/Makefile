default: help

help: 		## Show help for each of the Makefile recipes
	@fgrep -h "##" $(MAKEFILE_LIST) \
	 	| fgrep -v fgrep \
		| fgrep -v internal | sed -e 's/\\$$//' | sed -e 's/##//'

# A bit of a Hack in order to force cleanup
# after stopping or exiting
dev:		## Sets up local development environment
	 @bash -c "trap 'trap - SIGINT SIGTERM ERR; \
		 $(MAKE) stop; \
		 exit 1' \
		 SIGINT SIGTERM ERR; \
		 $(MAKE) stop && \
		 $(MAKE) start"

stop: 		## Stops and cleans up all containers
	@echo "\n>>> STOPPING DANGLING CONTAINERS <<<\n"
	@docker compose down --remove-orphans

start: 		## Starts local containers
	@echo "\n>>> STARTING API IN DEV MODE <<<\n"
	@docker compose up --build

test:		## Runs the go tests 
	@go test ./... -p 1

test-db: 	## Starts up the test database in the devops directory
	$(MAKE) -C ../devops test-db
