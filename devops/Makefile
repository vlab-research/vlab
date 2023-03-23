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
