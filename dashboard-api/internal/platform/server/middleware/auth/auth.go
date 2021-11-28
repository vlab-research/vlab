package auth

import (
	"log"
	"net/http"
	"net/url"
	"time"

	jwtmiddleware "github.com/auth0/go-jwt-middleware"
	"github.com/auth0/go-jwt-middleware/validate/josev2"
	"github.com/gin-gonic/gin"
	"gopkg.in/square/go-jose.v2"
	"gopkg.in/square/go-jose.v2/jwt"
)

func EnsureValidTokenMiddleware(domain, audience string) gin.HandlerFunc {
	issuerURL, err := url.Parse(domain)
	if err != nil {
		log.Fatalf("EnsureValidTokenMiddleware: failed to parse the issuer url: %v", err)
	}

	keyFunc := josev2.NewCachingJWKSProvider(*issuerURL, 5*time.Minute).KeyFunc
	expectedClaimsFunc := func() jwt.Expected {
		return jwt.Expected{
			Issuer:   domain,
			Audience: []string{audience},
		}
	}

	validator, err := josev2.New(
		keyFunc,
		jose.RS256,
		josev2.WithExpectedClaims(expectedClaimsFunc),
	)
	if err != nil {
		log.Fatalf("EnsureValidTokenMiddleware: failed to set up the josev2 validator: %v", err)
	}

	/*
		This error handler func is required to override the default behaviour of the jwtmiddleware
		which writes to the headers and body of the response upon error.
	*/
	noopErrorHandlerFunc := func(w http.ResponseWriter, r *http.Request, err error) {}
	middleware := jwtmiddleware.New(validator.ValidateToken, jwtmiddleware.WithErrorHandler(noopErrorHandlerFunc))

	return func(ctx *gin.Context) {
		var encounteredError = true

		var handler http.HandlerFunc = func(w http.ResponseWriter, r *http.Request) {
			encounteredError = false
			ctx.Request = r
			ctx.Next()
		}

		middleware.CheckJWT(handler).ServeHTTP(ctx.Writer, ctx.Request)

		if encounteredError {
			ctx.AbortWithStatusJSON(http.StatusUnauthorized, gin.H{"error": "JWT is invalid"})
		}
	}
}

func GetUserIdFrom(ctx *gin.Context) string {
	return ctx.Request.Context().Value(jwtmiddleware.ContextKey{}).(*josev2.UserContext).RegisteredClaims.Subject
}
