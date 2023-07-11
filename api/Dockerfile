# Note this Dockerfile hase been created to
# be build from the root of the vlab repo
FROM golang:alpine AS build

RUN apk --no-cache add ca-certificates
WORKDIR /src/app
# We have a dependency on some types in inference
COPY inference /src/inference
# First download dependencies in order to help with caching
COPY api/go.* ./
RUN go mod download
COPY api/ .
RUN CGO_ENABLED=0 go build -o /src/app/api /src/app/cmd/api/main.go

# Building image with the binary
FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=build /src/app/api /src/app/api
ENTRYPOINT ["/src/app/api"]
