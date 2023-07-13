package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"log"
	// "github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
	"github.com/vlab-research/vlab/inference/sources/types"
	"net/http"
)

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type AuthParams struct {
	GrantType string `url:"grant_type,omitempty"`
}

type AuthResponse struct {
	AccessToken string `json:"access_token"`
	ExpiresIn   int    `json:"expires_in"`
	Scope       string `json:"scope"`
	TokenType   string `json:"token_type"`
}

type QualtricsError struct {
	Meta struct {
		HTTPStatus string `json:"httpStatus"`
		RequestID  string `json:"requestId"`
		Notice     string `json:"notice"`
		Error      struct {
			ErrorMessage string `json:"errorMessage"`
			ErrorCode    string `json:"errorCode"`
		} `json:"error"`
	} `json:"meta"`
}

func (e *QualtricsError) Empty() bool {
	return e.Meta.Error.ErrorCode == ""
}

func (e *QualtricsError) Error() string {
	return e.Meta.Error.ErrorMessage

}

func basicAuth(username, password string) string {
	auth := username + ":" + password
	return base64.StdEncoding.EncodeToString([]byte(auth))
}

func Auth(client *http.Client, baseURL, clientID, clientSecret string) (string, error) {

	authString := basicAuth(clientID, clientSecret)
	auth := fmt.Sprintf("Basic %s", authString)

	sli := sling.New().Client(client).Base(baseURL).Set("Accept", "application/json").Set("Authorization", auth)

	res := new(AuthResponse)
	apiError := new(QualtricsError)

	authParams := &AuthParams{"client_credentials"}

	_, err := sli.New().Post("/oauth2/token").BodyForm(authParams).Receive(res, apiError)

	if err != nil {
		return "", err
	}

	if !apiError.Empty() {
		return "", apiError
	}

	return res.AccessToken, nil
}

type CreateExportRequest struct {
	Format string `json:"format"`
}
type CreateExportResponse struct {
	Result struct {
		ProgressID      string `json:"progressId"`
		PercentComplete int    `json:"percentComplete"`
		Status          string `json:"status"`
	} `json:"result"`
}

type ExportProgressResponse struct {
	Result struct {
		PercentComplete float64 `json:"percentComplete"`
		FileID          string  `json:"fileId"`
		Status          string  `json:"status"`
	} `json:"result"`
}

func CreateExport(client *http.Client, baseUrl string, survey int, apiToken string) (string, error) {

	// TODO: move out of here and into TypeformConnector
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("X-API-TOKEN", apiToken)

	res := new(CreateExportResponse)
	apiError := new(QualtricsError)

	url := fmt.Sprintf("/API/v3/surveys/%d/export-responses", survey)
	body := &CreateExportRequest{"json"}

	_, err := sli.New().Post(url).BodyJSON(body).Receive(res, apiError)

	if err != nil {
		return "", err
	}

	if !apiError.Empty() {
		return "", apiError
	}

	// ideally, this means the create export succeeeded!
	// TODO: validate this somehow?? Hard to do... I know a non-200 code should imply that

	progressID := res.Result.ProgressID

	if progressID == "" {
		return "", fmt.Errorf("Error creating export, progress ID came out empty")
	}

	url = fmt.Sprintf("/API/v3/surveys/%d/export-responses/%s", survey, progressID)

	progressRes := new(CreateExportResponse)
	apiError = new(QualtricsError)

	_, err = sli.New().Get(url).Receive(progressRes, apiError)

	if err != nil {
		return "", err
	}

	if !apiError.Empty() {
		return "", apiError
	}

	if progressRes.Result.Status == "inProgress" {
		// repeat
	}

	// get fileId

	// get file URL??

	// UNZIP?!!?!?

	return progressID, nil
}

func GetCredentials(source *Source) (*types.QualtricsCredentials, error) {
	details := source.Credentials.Details
	creds := new(types.QualtricsCredentials)
	err := json.Unmarshal(details, creds)
	return creds, err
}

func GetConfig(source *Source) (*QualtricsConfig, error) {
	b := source.Conf.Config
	conf := new(QualtricsConfig)
	err := json.Unmarshal(b, conf)
	return conf, err
}

type QualtricsConfig struct {
	SurveyName string `json:"survey_name"`
}

type QualtricsConnector struct {
	BaseURL string `env:"QUALTRICS_BASE_URL,required"`
}

func (c *QualtricsConnector) loadEnv() *QualtricsConnector {
	err := env.Parse(c)
	handle(err)
	return c
}

func main() {
	c := QualtricsConnector{}
	c.loadEnv()
	// connector.LoadEvents(c, "qualtrics", "idx")

	// https://stoplight.io/mocks/qualtricsv2/publicapidocs/60934
}
