function cleanup {
  ./stop.sh
}

trap cleanup EXIT
cleanup

echo "\n>>> STARTING API IN DEV MODE <<<\n"
docker-compose -f docker-compose-common.yaml -f docker-compose-dev.yaml up --build