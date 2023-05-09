FROM golang:alpine AS build

# Build Args
# The path to the app being built is passed via docker commands
ARG APP_PATH

RUN apk add --no-cache \
        gcc \
        libc-dev

WORKDIR /app

# The root of the repository has the module info
COPY go.mod .
COPY go.sum .
RUN go mod download

# Add all shared packages
COPY connector/ connector/
COPY inference-data/ inference-data/
COPY sources/types sources/types

# Build the app by copying only its files
COPY ${APP_PATH}/ ${APP_PATH}/
RUN CGO_ENABLED=0 go build -o /app/main ./${APP_PATH}

# Final Image using a distroless images
FROM gcr.io/distroless/static-debian11

COPY --from=build /app/main /

ENTRYPOINT ["/main"]
