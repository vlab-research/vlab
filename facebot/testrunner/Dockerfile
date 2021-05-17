FROM node:10-stretch

WORKDIR /usr/src/app

RUN npm install node-rdkafka
COPY package.json .
RUN npm i

COPY . .

CMD [ "npm", "test"]
