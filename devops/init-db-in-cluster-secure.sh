DB_HOST=$1
DB_NAME=$2
POD_NAME=$3

# NOTE: you'll need to create a database user + password first!
# TODO: you should transition to certs and mount them...

echo "create database ${DB_NAME};" | kubectl exec -i $POD_NAME -- ./cockroach sql --certs-dir=/cockroach/cockroach-certs --host $DB_HOST

cat sql/* | kubectl exec -i $POD_NAME -- ./cockroach sql --certs-dir=/cockroach/cockroach-certs --host $DB_HOST --database $DB_NAME
