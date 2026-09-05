
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

# Runs the REAL dashboard TypeScript (strata.ts, extract.ts) over the case set
# in the generator and records what it returns. Nothing Python touches the
# fixtures — that is what makes authoring/test_conformance.py a differential
# test of the port rather than a restatement of it. The generator is seeded, so
# regenerating without changing it reproduces the file byte for byte.
.PHONY: authoring-fixtures
authoring-fixtures:	## Regenerates authoring/conformance_fixtures.json from the dashboard TypeScript
	@[ -d ../dashboard/node_modules ] || (cd ../dashboard && npm ci)
	@cd ../dashboard && npx --yes tsx scripts/authoring-conformance.ts \
		> $(CURDIR)/adopt/authoring/conformance_fixtures.json
