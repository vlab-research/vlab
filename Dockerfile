FROM node:10-stretch

WORKDIR /usr/src/app

COPY package.json /usr/src/app
RUN npm i

COPY . /usr/src/app

CMD [ "npm", "start"]
