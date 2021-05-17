FROM node:10-stretch

WORKDIR /usr/src/app

RUN npm install node-rdkafka
COPY package.json /usr/src/app
RUN npm install

COPY . /usr/src/app

CMD [ "npm", "start"]
