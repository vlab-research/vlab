package testhelpers

import (
	"net/http"
	"net/http/httptest"
	"net/url"

	fb "github.com/huandu/facebook/v2"
)

var baseURLPath = "/"

func GetFBTestApp() (
	a *fb.App,
	teardown func(),
) {
	a = fb.New("foo", "bar")
	s, teardown := GetFBSession()
	a.SetSession(s)
	return a, teardown
}

// GetFBSession Returns a Mock Server in order to mock facebook
func GetFBSession() (
	session *fb.Session,
	teardown func(),
) {
	// mux is the HTTP request multiplexer used with the test server.
	mux := http.NewServeMux()

	// server is a test HTTP server used to provide mock API responses.
	server := httptest.NewServer(mux)

	url, _ := url.Parse(server.URL + baseURLPath)
	s := &fb.Session{
		BaseURL: url.String(),
	}

	// This is just some default handlers to make testing easier
	// code: valid => successful generations
	// default => No response which is an error
	mux.HandleFunc(
		"/oauth/access_token",
		func(w http.ResponseWriter, r *http.Request) {
			r.ParseForm()
			switch r.FormValue("code") {
			case "valid":
				w.Write([]byte(`{
					"expires_in": 5181452,
					"access_token": "supersecret",
					"token_type": "bearer"
				}`))
				w.WriteHeader(http.StatusCreated)
			default:
				w.WriteHeader(http.StatusBadRequest)
				return
			}
		})
	return s, server.Close
}
