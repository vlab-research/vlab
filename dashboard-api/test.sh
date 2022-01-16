docker-compose -f docker-compose-test.yaml down --remove-orphans

docker-compose -f docker-compose-test.yaml build setup_cockroachdb
docker-compose -f docker-compose-test.yaml run setup_cockroachdb

docker-compose -f docker-compose-test.yaml build api
docker-compose -f docker-compose-test.yaml run api
