#!/bin/bash

echo "START SETTING UP DB"

./cockroach sql --host=cockroachdb:26257 --insecure -e "CREATE DATABASE vlab"
./cockroach sql --host=cockroachdb:26257 --insecure --database=vlab < /seed_cockroachdb.sql

echo "FINISHED SETTING UP DB"