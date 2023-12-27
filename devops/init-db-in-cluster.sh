DB_HOST=$1
DB_NAME=$2
DB_VERSION="v21.2.17"

# NOTE: insecure version - need another script for secure...

echo "create database ${DB_NAME};" | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:$DB_VERSION --restart=Never --command -- ./cockroach sql --insecure --host $DB_HOST

cat sql/* | kubectl run -i --rm cockroach-client --image=cockroachdb/cockroach:$DB_VERSION --restart=Never --command -- ./cockroach sql --insecure --host $DB_HOST --database $DB_NAME
