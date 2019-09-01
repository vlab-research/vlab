FROM node:10-stretch

WORKDIR /usr/src/app

RUN npm install node-rdkafka
COPY package.json /usr/src/app
RUN npm i

COPY . /usr/src/app

EXPOSE 3000
EXPOSE 4000

CMD [ "npm", "start"]
