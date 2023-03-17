# VLAB Dashboard API

## Development

This application is written in go, and makes use of docker for local
development, please make sure you have the following dependencies installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Golang](https://go.dev/doc/install)

In order to enhance development experience there is some make targets to setup
your local environment

```bash
$ make
help:      Show help for each of the Makefile recipes
dev:       Sets up local development environment
stop:      Stops and cleans up all containers
start:     Starts local containers
test:      Runs the go tests 
```

In order to start the local development environment run you will need to setup
your environment variablse, you can do this by:

```bash
cp .env-exampl .env
```

You can now navigate to the `.env` file and make sure all required values are
set. Once done you can run:

```bash
make dev
```

### Running Tests

To run tests you need to start up the test database:

```
cd ../devops
./test_db.sh
cd ../dashboard-api
```
Then you should be able to run the tests as usual

```bash
make test
```
> This will run all go tests for this application with verbose output

