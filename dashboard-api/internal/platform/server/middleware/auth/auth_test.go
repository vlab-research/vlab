package auth

import (
	"crypto/rand"
	"crypto/rsa"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/go-playground/assert/v2"
	"gopkg.in/square/go-jose.v2"
	"gopkg.in/square/go-jose.v2/jwt"
)

func TestEnsureValidTokenMiddleware(t *testing.T) {
	audience := "aud"
	jwk := GenerateJWK(t)
	testServer := SetupTestJWKServer(t, jwk)
	defer testServer.Close()

	t.Run("invalid token due to audience", func(t *testing.T) {
		token := BuildJWTForTesting(
			t,
			jwk,
			testServer.URL,
			"subject",
			[]string{"test"},
		)
		req, _ := http.NewRequest(http.MethodGet, "", nil)
		req.Header.Set("Authorization", "Bearer "+token)
		resp := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(resp)
		c.Request = req
		EnsureValidTokenMiddleware(testServer.URL, audience)(c)
		assert.Equal(t, resp.Code, 401)
	})
	t.Run("valid token", func(t *testing.T) {
		token := BuildJWTForTesting(
			t,
			jwk,
			testServer.URL,
			"subject",
			[]string{audience},
		)
		req, _ := http.NewRequest(http.MethodGet, "", nil)
		req.Header.Set("Authorization", "Bearer "+token)
		resp := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(resp)
		c.Request = req
		EnsureValidTokenMiddleware(testServer.URL, audience)(c)
		assert.Equal(t, resp.Code, 200)
	})

}

// GenerateJWK generates a JWK for testing purposes
// TODO: Move to internal/testhelpers, currently not possible due to cycle
// import
func GenerateJWK(t *testing.T) *jose.JSONWebKey {
	t.Helper()

	privateKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		t.Fatal("failed to generate private key")
	}

	return &jose.JSONWebKey{
		Key:       privateKey,
		KeyID:     "kid",
		Algorithm: string(jose.RS256),
		Use:       "sig",
	}
}

// SetupTestJWKServer creates a fake server to respond to JWK requests
// TODO: Move to internal/testhelpers, currently not possible due to cycle
// import
func SetupTestJWKServer(
	t *testing.T,
	jwk *jose.JSONWebKey,
) (server *httptest.Server) {
	t.Helper()

	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.String() {
		case "/.well-known/openid-configuration":
			wk := struct {
				JWKSURI string `json:"jwks_uri"`
			}{
				JWKSURI: server.URL + "/.well-known/jwks.json",
			}
			if err := json.NewEncoder(w).Encode(wk); err != nil {
				t.Fatal(err)
			}
		case "/.well-known/jwks.json":
			if err := json.NewEncoder(w).Encode(jose.JSONWebKeySet{
				Keys: []jose.JSONWebKey{jwk.Public()},
			}); err != nil {
				t.Fatal(err)
			}
		default:
			t.Fatalf("was not expecting to handle the following url: %s", r.URL.String())
		}
	})

	return httptest.NewServer(handler)
}

// BuildJWTForTesting helper to create a valid JWT
// TODO: Move to internal/testhelpers, currently not possible due to cycle
// import
func BuildJWTForTesting(
	t *testing.T,
	jwk *jose.JSONWebKey,
	issuer, subject string,
	audience []string,
) string {
	t.Helper()

	key := jose.SigningKey{
		Algorithm: jose.SignatureAlgorithm(jwk.Algorithm),
		Key:       jwk,
	}

	signer, err := jose.NewSigner(key, (&jose.SignerOptions{}).WithType("JWT"))
	if err != nil {
		t.Fatalf("could not build signer: %s", err.Error())
	}

	claims := jwt.Claims{
		Issuer:   issuer,
		Audience: audience,
		Subject:  subject,
	}

	token, err := jwt.Signed(signer).Claims(claims).CompactSerialize()
	if err != nil {
		t.Fatalf("could not build token: %s", err.Error())
	}

	return token
}
