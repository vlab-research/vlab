default: help

help: 		## Show help for each of the Makefile recipes
	@fgrep -h "##" $(MAKEFILE_LIST) \
	 	| fgrep -v fgrep \
		| fgrep -v internal | sed -e 's/\\$$//' | sed -e 's/##//'

build:		## Used to build the binary
	@CGO_ENABLED=0 go build cmd/api/main.go	

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

start-ci:	## Starts local containers
	@echo "\n>>> STARTING API IN DEV MODE <<<\n"
	@docker compose up --build -d

test:		## Runs the go tests 
	@go test ./... -p 1


reset-seed:	## Resets the seeds in the database
	$(MAKE) seed-down seed-up

seed-down:	## Removes the seed data from the database
	@docker run \
		--net=host \
		--rm \
		--volume $(shell pwd)/../devops/seeds:/seeds:rw \
		migrate/migrate:v4.15.2 \
    -database "cockroach://root@localhost:5432/vlab?sslmode=disable&x-migrations-table=seeds" \
		-path /seeds \
		down -all

seed-up:	## Adds the seed data to the database
	@docker run \
		--net=host \
		--rm \
		--volume $(shell pwd)/../devops/seeds:/seeds:rw \
		migrate/migrate:v4.15.2 \
    -database "cockroach://root@localhost:5432/vlab?sslmode=disable&x-migrations-table=seeds" \
		-path /seeds \
		up
		

test-db: 	## Starts up the test database in the devops directory
	$(MAKE) -C ../devops test-db
