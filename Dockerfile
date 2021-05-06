FROM python:3.9

WORKDIR /usr/src/app

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false
COPY poetry.lock pyproject.toml ./

RUN poetry install --no-dev

COPY . .

CMD [ "python", "./malaria.py" ]
