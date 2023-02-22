package auth

import (
	"crypto/rand"
	"crypto/rsa"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"gopkg.in/go-jose/go-jose.v2"
	"gopkg.in/go-jose/go-jose.v2/jwt"
)

func TestEnsureValidTokenMiddleware(t *testing.T) {
	domain := "example.com"
	audience := "aud"
	jwk := generateJWK(t)
	testServer := setupTestServer(t, jwk)
	defer testServer.Close()

	t.Run("invalid token", func(t *testing.T) {
		token := buildJWTForTesting(
			t,
			jwk,
			testServer.URL,
			"subject",
			[]string{"aud"},
		)
		req := httptest.NewRequest(http.MethodGet, "/", nil)
		req.Header.Set("Authorization", "Bearer "+token)
		resp := httptest.NewRecorder()

		c, _ := gin.CreateTestContext(resp)
		EnsureValidTokenMiddleware(domain, audience)(c)

		assert.Equal(t, http.StatusUnauthorized, resp.Code)
		assert.JSONEq(t, `{"error": "Unauthorized"}`, resp.Body.String())
	})

}

func generateJWK(t *testing.T) *jose.JSONWebKey {
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

func setupTestServer(
	t *testing.T,
	jwk *jose.JSONWebKey,
) (server *httptest.Server) {
	t.Helper()

	var handler http.Handler = http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
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

func buildJWTForTesting(
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
