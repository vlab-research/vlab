FROM python:3.8

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install git+https://github.com/nandanrao/typedjson-python

COPY . .

CMD [ "python", "./malaria.py" ]
