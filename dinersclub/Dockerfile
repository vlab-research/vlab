FROM golang:alpine AS build
RUN apk add --no-cache \
        gcc \
        libc-dev \
        librdkafka-dev=1.8.2-r0 --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community \
        pkgconf
RUN mkdir /app
WORKDIR /app

COPY go.mod .
COPY go.sum .
RUN go mod download
COPY . /app/
RUN go build -tags dynamic -a -o main .


FROM alpine
RUN apk add --no-cache \
        librdkafka-dev=1.8.2-r0 --repository=http://dl-cdn.alpinelinux.org/alpine/edge/community
WORKDIR /app
COPY --from=build /app/main /app/
CMD ["/app/main"]
