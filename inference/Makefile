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

