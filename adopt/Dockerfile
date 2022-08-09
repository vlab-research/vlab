FROM python:3.9

WORKDIR /usr/src/app

RUN pip install pdm

RUN pdm config python.use_venv false

COPY pdm.lock pyproject.toml ./

RUN pdm install --prod --no-lock --no-editable

ENV PYTHONPATH=/usr/src/app/__pypackages__/3.9/lib

COPY . .

CMD [ "python", "./malaria_ads.py" ]
