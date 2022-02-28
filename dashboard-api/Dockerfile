FROM golang:alpine AS build

RUN apk --no-cache add ca-certificates
WORKDIR /app
COPY . .
RUN CGO_ENABLED=0 go build -o /app/api cmd/api/main.go

# Building image with the binary
FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /app/api /app/api
ENTRYPOINT ["/app/api"]