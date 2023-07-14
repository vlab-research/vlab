package main

import (
	"archive/zip"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"log"
	"time"
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

type CreateExportRequest struct {
	Format string `json:"format"`
}
type CreateExportResponse struct {
	Result struct {
		ProgressID      string  `json:"progressId"`
		PercentComplete float64 `json:"percentComplete"`
		Status          string  `json:"status"`
	} `json:"result"`
}

type ExportProgressResponse struct {
	Result struct {
		PercentComplete float64 `json:"percentComplete"`
		FileID          string  `json:"fileId"`
		Status          string  `json:"status"`
	} `json:"result"`
}

func CreateExport(client *http.Client, baseUrl string, survey string, apiToken string) (string, error) {

	// TODO: move out of here and into TypeformConnector
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("X-API-TOKEN", apiToken)

	res := new(CreateExportResponse)
	apiError := new(QualtricsError)

	url := fmt.Sprintf("/API/v3/surveys/%s/export-responses", survey)
	body := &CreateExportRequest{"json"}

	_, err := sli.New().Post(url).BodyJSON(body).Receive(res, apiError)

	fmt.Println(err)
	if err != nil {
		return "", err
	}

	if !apiError.Empty() {
		return "", apiError
	}

	progressID := res.Result.ProgressID

	if progressID == "" {
		return "", fmt.Errorf("Error creating export, progress ID came out empty")
	}

	url = fmt.Sprintf("/API/v3/surveys/%s/export-responses/%s", survey, progressID)

	progressRes := new(ExportProgressResponse)
	for {

		apiError = new(QualtricsError)

		_, err = sli.New().Get(url).Receive(progressRes, apiError)

		if err != nil {
			return "", err
		}

		if !apiError.Empty() {
			return "", apiError
		}

		if progressRes.Result.Status == "complete" {
			break
		}

		time.Sleep(time.Second)
	}

	// Add base urL??
	path := fmt.Sprintf("/API/v3/surveys/%s/export-responses/%s/file", survey, progressRes.Result.FileID)

	return path, nil
}

func ReadZippedCSV(path string) {
	r, err := zip.OpenReader(path)
	if err != nil {
		log.Fatal(err)
	}
	defer r.Close()

	for _, f := range r.File {
		rc, err := f.Open()
		if err != nil {
			log.Fatal(err)
		}

		reader := csv.NewReader(rc)
		rows, err := reader.ReadAll()
		if err != nil {
			log.Fatal(err)
		}

		_ = rows[0]

		for _, r := range rows[1:] {
			fmt.Println(r)
		}

		rc.Close()
	}
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
