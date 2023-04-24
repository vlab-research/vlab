package auth

import (
	"log"
	"net/http"
	"net/url"
	"time"

	jwtmiddleware "github.com/auth0/go-jwt-middleware/v2"
	"github.com/auth0/go-jwt-middleware/v2/jwks"
	"github.com/auth0/go-jwt-middleware/v2/validator"
	"github.com/gin-gonic/gin"
)

// EnsureValidTokenMiddleware is gin middleware to verify the authenticity of a JWT
// token sent from a client to authenticated endpoints
func EnsureValidTokenMiddleware(domain, audience string) gin.HandlerFunc {

	issuerURL, err := url.Parse(domain)
	if err != nil {
		log.Fatalf("EnsureValidTokenMiddleware: failed to parse the issuer url: %v", err)
	}

	provider := jwks.NewCachingProvider(issuerURL, 5*time.Minute)

	validator, err := validator.New(
		provider.KeyFunc,
		validator.RS256,
		issuerURL.String(),
		[]string{audience},
	)

	if err != nil {
		log.Fatalf(
			"EnsureValidTokenMiddleware: failed to set up the JWT validator: %v", err,
		)
	}

	/*
		This error handler func is required to override the default behaviour of the
		jwtmiddleware which writes to the headers and body of the response upon error.
	*/
	noopErrorHandlerFunc := func(w http.ResponseWriter, r *http.Request, err error) {}
	middleware := jwtmiddleware.New(
		validator.ValidateToken,
		jwtmiddleware.WithErrorHandler(noopErrorHandlerFunc),
	)

	return func(ctx *gin.Context) {
		var encounteredError = true

		var handler http.HandlerFunc = func(w http.ResponseWriter, r *http.Request) {
			encounteredError = false
			ctx.Request = r
			ctx.Next()
		}

		middleware.CheckJWT(handler).ServeHTTP(ctx.Writer, ctx.Request)

		if encounteredError {
			ctx.AbortWithStatusJSON(
				http.StatusUnauthorized,
				gin.H{"error": "JWT is invalid"},
			)
		}
	}
}

// GetUserIdFrom gets the registered users ID from the gin context
func GetUserIdFrom(ctx *gin.Context) string {
	return ctx.Request.Context().Value(jwtmiddleware.ContextKey{}).(*validator.ValidatedClaims).RegisteredClaims.Subject
}
