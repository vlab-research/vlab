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
test-db: 	 Starts up the test database in the devops directory
```

In order to start the local development environment you will need to setup
your environment variables, you can do this by:

```bash
cp .env-example .env
```

You can now navigate to the `.env` file and make sure all required values are
set. Once done you can run:

```bash
make dev
```
> Note this will start the development backend with seeded data. You will be
able to access this when logging in with the `demo@vlab.digital` user

### Running Tests

To run tests you need to start up the test database:

```
make test-db
```

Then you should be able to run the tests as usual

```bash
make test
```
> This will run all go tests for this application however it runs them
synchronously as we have tests that affect each other when run in parallel

