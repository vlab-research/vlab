FROM golang:alpine AS build
RUN apk add --no-cache \
        gcc \
        libc-dev
RUN mkdir /app
WORKDIR /app

# The root of the repository has the module info
ADD go.mod .
ADD go.sum .
RUN go mod download

# The path to the app being built is passed via docker commands
ARG APP_PATH

# Add all shared packages
# NOTE: this is just an optimization which makes it faster
#       than adding all files, but that would work too.
ADD ./inference/connector /app/inference/connector/
ADD ./inference/inference-data /app/inference/inference-data/

# Build the app by copying its files to root
ADD ${APP_PATH} /app/
RUN go build -o main .


FROM alpine
ARG APP_PATH
WORKDIR /app
COPY --from=build /app/main /app/

CMD ["/app/main"]
