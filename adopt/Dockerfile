# Tracks the CEILING of pyproject.toml's `python = ">=3.10,<3.13"`, not the
# floor: production runs the newest interpreter the package supports, and CI's
# `tests` matrix is what keeps the 3.10 floor honest. Lifted from 3.10-slim
# under VIR-47 Phase B -- see planning/pandas2-numpy2-python-upgrade.md.
FROM python:3.12-slim

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

RUN poetry install --only main --no-root

COPY . .

CMD [ "python", "./malaria.py" ]
