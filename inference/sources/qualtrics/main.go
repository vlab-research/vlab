package main

import (
	"archive/zip"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"os"

	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"

	// "strings"
	"net/http"
	"time"

	"github.com/google/uuid"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
	"github.com/vlab-research/vlab/inference/sources/types"
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
	Format                 string `json:"format"`
	SortByLastModifiedDate bool   `json:"sortByLastModifiedDate,omitempty"`
	AllowContinuation      bool   `json:"allowContinuation,omitempty"`
	ContinuationToken      string `json:"continuationToken,omitempty"`
}

type CreateExportResponse struct {
	Result struct {
		ProgressID        string  `json:"progressId"`
		PercentComplete   float64 `json:"percentComplete"`
		Status            string  `json:"status"`
	} `json:"result"`
}

type ExportProgressResponse struct {
	Result struct {
		PercentComplete float64 `json:"percentComplete"`
		FileID          string  `json:"fileId"`
		Status          string  `json:"status"`
		ContinuationToken string  `json:"continuationToken"`
	} `json:"result"`
}

func CreateExport(sli *sling.Sling, survey string, wait float64, maxAttempts int, pagination string) (string, string, error) {

	// TODO: move out of here and into TypeformConnector

	res := new(CreateExportResponse)
	apiError := new(QualtricsError)

	url := fmt.Sprintf("/API/v3/surveys/%s/export-responses", survey)

	body := &CreateExportRequest{
		Format: "json", 
	}

	if pagination != "" {
		body.ContinuationToken = pagination
	} else  {
		body.AllowContinuation = true 
		body.SortByLastModifiedDate = true
	}

	_, err := sli.New().Post(url).BodyJSON(body).Receive(res, apiError)

	if err != nil {
		return "", "", err
	}

	if !apiError.Empty() {
		return "", "", apiError
	}

	progressID := res.Result.ProgressID

	if progressID == "" {
		return "", "", fmt.Errorf("Error creating export, progress ID came out empty")
	}

	log.Println(fmt.Sprintf("Created export with progress ID: %s", progressID))

	url = fmt.Sprintf("/API/v3/surveys/%s/export-responses/%s", survey, progressID)

	progressRes := new(ExportProgressResponse)
	attempts := 1
	for {

		log.Println(fmt.Sprintf("Polling for response export. Attempt: %d", attempts))

		apiError = new(QualtricsError)

		_, err = sli.New().Get(url).Receive(progressRes, apiError)

		if err != nil {
			return "", "", err
		}

		if !apiError.Empty() {
			return "", "", apiError
		}

		if progressRes.Result.Status == "complete" {
			break
		}

		if attempts >= maxAttempts {
			return "", "", fmt.Errorf("Giving up on file export for survey %s after %d attempts", survey, attempts)
		}

		attempts++
		time.Sleep(time.Duration(wait) * time.Second)
	}

	// Add balse urL??
	path := fmt.Sprintf("/API/v3/surveys/%s/export-responses/%s/file", survey, progressRes.Result.FileID)

	log.Println(fmt.Sprintf("Export complete. Path to file: %s", path))

	return progressRes.Result.ContinuationToken, path, nil
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

func DownloadFile(client *http.Client, sli *sling.Sling, path string) (string, error) {

	log.Println(fmt.Sprintf("Download file from path: %s", path))

	filePath := fmt.Sprintf("/tmp/%s.zip", uuid.New())

	req, err := sli.New().Get(path).Request()
	if err != nil {
		return "", err
	}
	resp, err := client.Do(req)
	if err != nil {
		return "", err
	}

	defer resp.Body.Close()

	// Create the file
	out, err := os.Create(filePath)
	if err != nil {
		return "", err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return "", err
	}

	log.Println("Downloaded zip file")

	return filePath, nil
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

type QualtricsValue struct {
	Label string `json:"label"`
	Value json.RawMessage `json:"value"`
}

func GetResponsesFromFile(source *Source, path string, idx int, pagination string) <-chan *InferenceDataEvent {
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

				label, ok := r.Labels[k]

				if !ok {
					label = ""
				}

				qv := QualtricsValue{Label: label, Value: v}

				b, err := json.Marshal(qv) 

				if err != nil {
					handle(err)
				}
				

				event := &InferenceDataEvent{
					User:       user,
					Study:      source.StudyID,
					SourceConf: source.Conf,
					Timestamp:  timestamp,
					Variable:   k,
					Value:      b,
					Idx:        idx,

					Pagination: pagination,
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

func MakeSling(client *http.Client, baseURL string, apiKey string) *sling.Sling {

	sli := sling.New().Client(client).Base(baseURL).Set("Accept", "application/json").Set("X-API-TOKEN", apiKey)
	return sli
}

func (c *QualtricsConnector) GetResponses(source *Source, config *QualtricsConfig, pagination string, idx int) <-chan *InferenceDataEvent {

	client := http.DefaultClient

	creds := parseCreds(source.Credentials.Details)
	sli := MakeSling(client, c.BaseURL, creds.APIKey)

	newPagination, filePath, err := CreateExport(sli, config.SurveyID, c.WaitTime, c.MaxAttempts, pagination)
	handle(err)

	path, err := DownloadFile(client, sli, filePath)
	handle(err)

	return GetResponsesFromFile(source, path, idx, newPagination)
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
