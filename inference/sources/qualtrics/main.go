package main

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"io"
	"log"
	// "strings"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
	"github.com/vlab-research/vlab/inference/sources/types"
	"net/http"
	"time"
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

func CreateExport(client *http.Client, baseUrl string, survey string, apiToken string, wait float64, maxAttempts int) (string, error) {

	// TODO: move out of here and into TypeformConnector
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("X-API-TOKEN", apiToken)

	res := new(CreateExportResponse)
	apiError := new(QualtricsError)

	url := fmt.Sprintf("/API/v3/surveys/%s/export-responses", survey)
	body := &CreateExportRequest{"json"}

	_, err := sli.New().Post(url).BodyJSON(body).Receive(res, apiError)

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
	attempts := 1
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

		if attempts >= maxAttempts {
			return "", fmt.Errorf("Giving up on file export for survey %s after %d attempts", survey, attempts)
		}

		attempts++
		time.Sleep(time.Duration(wait) * time.Second)
	}

	// Add base urL??
	path := fmt.Sprintf("/API/v3/surveys/%s/export-responses/%s/file", survey, progressRes.Result.FileID)

	return path, nil
}

type RawQualtricsResponse struct {
	ResponseID      string                     `json:"responseId"`
	Values          map[string]json.RawMessage `json:"values,omitempty"`
	Labels          map[string]string          `json:"labels,omitempty"`
	DisplayedFields []string                   `json:"displayedFields"`
	DisplayedValues map[string][]int           `json:"displayedValues,omitempty"`
	RecordedDate    time.Time
	StartDate       time.Time
}

type QualtricsResponse RawQualtricsResponse

func parseDates(m map[string]json.RawMessage, keys []string) (map[string]time.Time, error) {
	format := time.RFC3339

	res := map[string]time.Time{}

	for _, key := range keys {
		b, ok := m[key]

		if !ok {
			continue
		}

		var s string
		err := json.Unmarshal(b, &s)
		if err != nil {
			return res, err
		}

		parsed, err := time.Parse(format, s)
		if err != nil {
			return res, err
		}

		res[key] = parsed
	}

	return res, nil
}

func (q *QualtricsResponse) UnmarshalJSON(b []byte) error {
	qq := new(RawQualtricsResponse)
	err := json.Unmarshal(b, qq)
	if err != nil {
		return err
	}

	keys := []string{"recordedDate", "startDate"}

	parsed, err := parseDates(qq.Values, keys)
	if err != nil {
		return err
	}

	qq.RecordedDate = parsed["recordedDate"]
	qq.StartDate = parsed["startDate"]

	*q = QualtricsResponse(*qq)
	return nil
}

type QualtricsResponseFile struct {
	Responses []QualtricsResponse `json:"responses"`
}

func parseJSONResponse(f *zip.File) (*QualtricsResponseFile, error) {
	rc, err := f.Open()
	defer rc.Close()

	if err != nil {
		return nil, err
	}

	s, err := io.ReadAll(rc)
	if err != nil {
		return nil, err
	}

	res := new(QualtricsResponseFile)
	err = json.Unmarshal(s, res)
	if err != nil {
		return nil, err
	}

	return res, nil
}

func DownloadFile(url string) (string, error) {
	// download from url
	// write output to path
	// return path of file

	return "", nil
}

func ReadZippedJSON(path string) (*QualtricsResponseFile, error) {
	r, err := zip.OpenReader(path)
	if err != nil {
		return nil, err
	}
	defer r.Close()

	for _, f := range r.File {
		return parseJSONResponse(f)
	}

	return nil, fmt.Errorf("No files found in %s", path)
}

func GetResponsesFromFile(source *Source, path string, idx int) <-chan *InferenceDataEvent {
	events := make(chan *InferenceDataEvent)

	responseFile, err := ReadZippedJSON(path)

	if err != nil {
		handle(err)
	}

	go func() {
		defer close(events)
		for _, r := range responseFile.Responses {

			user := User{ID: r.ResponseID}
			timestamp := r.RecordedDate

			for k, v := range r.Values {
				idx++

				event := &InferenceDataEvent{
					User:       user,
					Study:      source.StudyID,
					SourceConf: source.Conf,
					Timestamp:  timestamp,
					Variable:   k,
					Value:      v,
					Idx:        idx,

					// NOTE: We have no pagination.
					// WHAT TO DO ????????????????
					Pagination: "",
				}
				events <- event
			}

		}
	}()

	return events
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
	SurveyID string `json:"survey_id"`
}

type QualtricsConnector struct {
	BaseURL     string  `env:"QUALTRICS_BASE_URL,required"`
	WaitTime    float64 `env:"EXPORT_POLLING_WAIT_TIME,required"`
	MaxAttempts int     `env:"EXPORT_POLLING_MAX_ATTEMPTS,required"`
}

func (c *QualtricsConnector) loadEnv() *QualtricsConnector {
	err := env.Parse(c)
	handle(err)
	return c
}

func parseCreds(b json.RawMessage) *types.QualtricsCredentials {
	creds := new(types.QualtricsCredentials)
	err := json.Unmarshal(b, creds)
	handle(err)
	return creds
}

func (c *QualtricsConnector) GetResponses(source *Source, config *QualtricsConfig, token string, idx int) <-chan *InferenceDataEvent {

	client := &http.Client{}

	creds := parseCreds(source.Credentials.Details)

	fileUrl, err := CreateExport(client, c.BaseURL, config.SurveyID, creds.APIKey, c.WaitTime, c.MaxAttempts)
	handle(err)

	path, err := DownloadFile(fileUrl)
	handle(err)

	return GetResponsesFromFile(source, path, idx)
}

func (c QualtricsConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	config := new(QualtricsConfig)
	err := json.Unmarshal(source.Conf.Config, config)
	handle(err)

	log.Println("Qualtrics connector getting data for: ", config)

	token := ""
	idx := 0

	if lastEvent != nil {
		token = lastEvent.Pagination
		idx = lastEvent.Idx
	}

	events := c.GetResponses(source, config, token, idx)
	return events
}

func main() {
	c := QualtricsConnector{}
	c.loadEnv()
	connector.LoadEvents(c, "qualtrics", "idx")
}
