## Databases

We currently use [CockroachDB](1) as our database, In order to facilate our
database migrations we have opted to use [go-migrate](2). This allows us to keep
schema changes in an ordered manner.

### Makefile Targets

```bash
$ make
help:       Show help for each of the Makefile recipes
migration:  Create a new migration file [name: required]
seed:       Create new seed file [name: required]
test-db:    Runs a test db used for the API tests 
```

### Creating a new migration

In order to create a new migration run:

```bash
make migration name=$MIGRATION_NAME
```
> A small note on this command, as we use docker and docker volumes to
generate this, there is a good change the files will be created in a read only
mode (specifically if you are using a linux machine). You will need to save them with sudo or admin

You will find a new migration file in the [migrations](./migrations) directory.
Please make sure to create the UP  and DOWN (rollback) migrations as well as
keep in mind that all migrations should try to be idempotent and backwards
compatible

### Creating a new seed

In order to create a new seed run:

```bash
make seed name=$MIGRATION_NAME
```
> A small note on this command, as we use docker and docker volumes to
generate this, there is a good change the files will be created in a read only
mode (specifically if you are using a linux machine). You will need to save them with sudo or admin

You will find a new seed file in the [seeds](./seeds) directory. Please be
mindful to fill in the UP and DOWN files, UP should create the seed and DOWN
should delete the seeds.

[1]: https://www.cockroachlabs.com/docs/
[2]: https://github.com/golang-migrate/migrate
