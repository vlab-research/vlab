default: build

build: fly typeform

swoosh: 
	@go build  -o swoosh swoosh/swoosh.go

.PHONY: fly
fly:
	@go build -o fly sources/fly/main.go

.PHONY: tyepform
typeform:
	@go build -o typeform sources/typeform/main.go

test:		## Runs the go tests 
	@go test ./... -p 1

test-db: 	## Starts up the test database in the devops directory
	$(MAKE) -C ../devops test-db
