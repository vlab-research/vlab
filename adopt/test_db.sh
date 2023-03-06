docker stop vlab-recruitment-test && docker rm vlab-recruitment-test

docker run --name vlab-recruitment-test -d -p 5433:26257 cockroachdb/cockroach:v21.1.7 start-single-node --insecure

# Need to wait for cockroachDB to start
sleep 5

echo "create database test;" | docker run -i --net=host --rm cockroachdb/cockroach:v21.1.7 sql --insecure --host localhost --port 5433 --database test

cat ../devops/sql/* | docker run -i --net=host --rm cockroachdb/cockroach:v21.1.7 sql --insecure --host localhost --port 5433 --database test
