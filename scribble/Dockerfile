FROM golang:alpine AS build
RUN sed -i -e 's/v[[:digit:]]\..*\//edge\//g' /etc/apk/repositories
RUN apk upgrade --update-cache --available
RUN apk add --no-cache \
        gcc \
        libc-dev \
        librdkafka-dev=1.8.2-r0 \
        pkgconf
RUN mkdir /app
WORKDIR /app

ADD go.mod .
ADD go.sum .
RUN go mod download
ADD . /app/
RUN go build -tags dynamic -a -o main .


FROM alpine
RUN sed -i -e 's/v[[:digit:]]\..*\//edge\//g' /etc/apk/repositories
RUN apk upgrade --update-cache --available

RUN apk add --no-cache \
        librdkafka-dev=1.8.2-r0
WORKDIR /app
COPY --from=build /app/main /app/
CMD ["/app/main"]
