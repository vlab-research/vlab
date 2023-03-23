#/bin/bash -ex

docker stop vlab-recruitment-test && docker rm vlab-recruitment-test

# Starts the database in single cluster mode
docker run \
  --name vlab-recruitment-test \
  -d \
  -p 5433:26257 \
  cockroachdb/cockroach:v21.1.7 \
  start-single-node \
  --insecure

# Runs the first migration that creates the database
echo "Setting Up Database"
docker run \
  --net=host \
  --rm \
  --volume $PWD/migrations:/migrations \
  migrate/migrate:v4.15.2 \
  -database cockroach://root@localhost:5433/defaultdb?sslmode=disable \
  -path /migrations/inittest \
  up

# Hack as docker run does not fail on errors
if [ $? -ne 0 ];
then
  exit $?
fi

# Runs all migrations in order to setup the database
echo "Running Migrations"
docker run \
  --net=host \
  --rm \
  --volume $PWD/migrations:/migrations \
  migrate/migrate:v4.15.2 \
  -database cockroach://root@localhost:5433/test?sslmode=disable \
  -path /migrations \
  up

# Hack as docker run does not fail on errors
if [ $? -ne 0 ];
then
  exit $?
fi
