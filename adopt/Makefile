
coverage:
	@poetry run coverage run -m pytest
	@poetry run coverage html --include='adopt/*'

.PHONY: test
test:		## Runs the go tests 
	@poetry run pytest .

test-db: 	## Starts up the test database in the devops directory
	$(MAKE) -C ../devops test-db
