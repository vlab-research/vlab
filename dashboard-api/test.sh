function cleanup {
  ./stop.sh
}

trap cleanup EXIT
cleanup

echo "\n>>> SETTING UP API <<<\n"
docker compose -f docker-compose-common.yaml -f docker-compose-test.yaml build api

echo "\n>>> RUNNING TEST CASES <<<\n"
docker compose -f docker-compose-common.yaml -f docker-compose-test.yaml run api
