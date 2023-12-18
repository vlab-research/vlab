FROM python:3.10-slim

WORKDIR /usr/src/app

RUN apt-get update && \
    apt-get install --yes \
    curl \
    git

RUN pip install --upgrade pip

RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH="/root/.local/bin:$PATH"

RUN poetry config virtualenvs.create false
COPY poetry.lock pyproject.toml ./

RUN poetry install --only main

COPY . .

CMD [ "python", "./malaria.py" ]
