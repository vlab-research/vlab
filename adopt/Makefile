
coverage:
	@poetry run coverage run -m pytest
	@poetry run coverage html --include='adopt/*'

.PHONY: test
test:		## Runs the go tests 
	@poetry run pytest .

test-db: 	## Starts up the test database in the devops directory
	$(MAKE) -C ../devops test-db

.PHONY: schemas
schemas:	## Regenerates the committed JSON Schemas in schemas/
	@poetry run python -m adopt.schema_export

# Needs no database: the export is a pure function of study_conf.py.
.PHONY: check-schemas
check-schemas:	## Fails if schemas/ has drifted from study_conf.py
	@poetry run python -m adopt.schema_export --check
