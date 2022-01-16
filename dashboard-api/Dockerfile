FROM golang:alpine AS build

RUN apk add --update git
RUN apk --no-cache add ca-certificates
WORKDIR /github.com/vlab-research/vlab/dashboard-api
COPY . .
RUN CGO_ENABLED=0 go build -o /go/bin/api cmd/api/main.go

# Building image with the binary
FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /go/bin/api /go/bin/api
ENTRYPOINT ["/go/bin/api"]

