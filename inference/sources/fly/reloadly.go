package main

import (
	"fmt"
	"net/http"
	"strings"

	"github.com/dghubble/sling"
)

type Service struct {
	Client       *http.Client
	BaseUrl      string
	AuthUrl      string
	Token        *Token
	id           string
	secret       string
	sandboxUrl   string
	acceptHeader string
}

func (s *Service) Sandbox() {
	s.BaseUrl = s.sandboxUrl
}

func (s *Service) request(sli *sling.Sling, method, path string, params interface{}, resp interface{}) (*http.Response, error) {
	switch strings.ToUpper(method) {
	case "GET":
		sli = sli.Get(path).QueryStruct(params)
	case "POST":
		sli = sli.Post(path).BodyJSON(params)
	}

	apiError := APIError{}
	httpResponse, err := sli.Receive(resp, &apiError)
	if err != nil {
		return nil, err
	}

	status := httpResponse.StatusCode

	if !apiError.Empty() {
		apiError = apiError.AddStatus(status)
		return httpResponse, apiError
	}

	// Reloadly will send an error response without
	// a body, sometimes, so we just create our
	// own "APIError" from the status.
	// TODO: remember when they do this...
	if status < 200 || status > 299 {
		return httpResponse, APIError{
			Message:    httpResponse.Status,
			ErrorCode:  fmt.Sprint(status),
			StatusCode: status,
		}
	}
	return httpResponse, nil
}

func (s *Service) Request(method, path string, params interface{}, resp interface{}) (*http.Response, error) {

	op := func() (*http.Response, error) {
		sli := sling.New().Client(s.Client).Base(s.BaseUrl).Set("Accept", s.acceptHeader)

		if s.Token != nil {
			auth := fmt.Sprintf("%v %v", s.Token.TokenType, s.Token.AccessToken)
			sli = sli.Set("Authorization", auth)
		}

		return s.request(sli, method, path, params, resp)
	}

	httpResponse, err := op()

	// If expired, try redoing the operation one time
	if err != nil {
		if e, ok := err.(APIError); ok && e.ErrorCode == "TOKEN_EXPIRED" {
			err = s.ReAuth()
			if err != nil {
				return nil, err
			}
			return op()
		}
	}

	return httpResponse, err
}
