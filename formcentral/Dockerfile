FROM golang:alpine AS build
RUN apk add --no-cache \
        gcc \
        libc-dev
RUN mkdir /app
WORKDIR /app

COPY go.mod .
COPY go.sum .
RUN go mod download
COPY . /app/
RUN go build -o main .


FROM alpine
WORKDIR /app
COPY --from=build /app/main /app/

EXPOSE 1323
CMD ["/app/main"]
