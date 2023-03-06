# adopt


## Configuration

Some documentation for configuring a vlab study:

## Development

### Setup local environment

This project requires the use of [Python Poetry](https://python-poetry.org/),
please see the [installation
guide](https://python-poetry.org/docs/#installation)

To install dependencies 
```bash
poetry install
```

### To Run Tests

The tests currently depend on a database running, to start the database

```bash
./test_db.sh
```

Then to run the tests
```bash
poetry run pytest .
```


