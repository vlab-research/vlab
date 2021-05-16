FROM golang:alpine AS build
RUN apk add --no-cache \
        gcc \
        libc-dev
RUN mkdir /app
WORKDIR /app

ADD go.mod .
ADD go.sum .
RUN go mod download
ADD . /app/
RUN go build -o main .


FROM alpine
WORKDIR /app
COPY --from=build /app/main /app/

EXPOSE 1323
CMD ["/app/main"]
