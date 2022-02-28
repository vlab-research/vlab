echo "\n>>> STOPPING DANGLING CONTAINERS <<<\n"

docker-compose -f docker-compose-common.yaml  -f docker-compose-dev.yaml down --remove-orphans
docker-compose -f docker-compose-common.yaml  -f docker-compose-test.yaml down --remove-orphans

echo "\n>>> FINISHED STOPPING DANGLING CONTAINERS <<<\n"