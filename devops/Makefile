default: help

help: 		## Show help for each of the Makefile recipes
	@fgrep -h "##" $(MAKEFILE_LIST) \
	 	| fgrep -v fgrep \
		| fgrep -v internal | sed -e 's/\\$$//' | sed -e 's/##//'


migration:	## Create a new migration file [name: required]
	@docker run \
		--net=host \
		--rm \
		-u $(id -u):$(id -g) \
		--volume ./migrations:/migrations:rw \
		migrate/migrate:v4.15.2 \
		create \
		-dir /migrations \
		-ext sql \
		$(name)

seed:		## Create new seed file [name: required]
	@docker run \
		--net=host \
		--rm \
		-u $(id -u):$(id -g) \
		--volume ./seeds:/seeds:rw \
		migrate/migrate:v4.15.2 \
		create \
		-dir /seeds \
		-ext sql \
		$(name)

test-db: 	## Runs a test db used for the API tests
	@ $(MAKE) start-db-container wait-for-db setup-database run-migrations

start-db-container:
	@-docker stop vlab-recruitment-test && docker rm vlab-recruitment-test
	@docker run \
  	--name vlab-recruitment-test \
  	-d \
  	-p 5433:26257 \
  	cockroachdb/cockroach:v24.1.28 \
  	start-single-node \
  	--insecure

wait-for-db:
	@echo "Waiting for CockroachDB to be ready..."
	@until docker exec vlab-recruitment-test ./cockroach sql --insecure -e "SELECT 1" > /dev/null 2>&1; do sleep 1; done

setup-database:
	@docker run \
  	--net=host \
  	--rm \
  	--volume $(shell pwd)/migrations:/migrations \
  	migrate/migrate:v4.15.2 \
  	-database cockroach://root@localhost:5433/defaultdb?sslmode=disable \
  	-path /migrations/inittest \
  	up
run-migrations:
	@docker run \
  	--net=host \
  	--rm \
  	--volume $(shell pwd)/migrations:/migrations \
  	migrate/migrate:v4.15.2 \
  	-database cockroach://root@localhost:5433/test?sslmode=disable \
  	-path /migrations \
  	up
