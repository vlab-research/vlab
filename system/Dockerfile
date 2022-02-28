FROM golang:alpine

RUN mkdir /app
COPY go.mod /app
WORKDIR /app

RUN go mod download
