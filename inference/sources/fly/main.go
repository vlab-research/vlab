package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"strings"
	"time"

	"github.com/caarlos0/env/v6"
	"github.com/dghubble/sling"
	"github.com/golang-jwt/jwt/v4"
	"github.com/vlab-research/vlab/inference/connector"
	. "github.com/vlab-research/vlab/inference/inference-data"
)

func (c flyConnector) GetToken(clientId, clientSecret string) string {
	url := "https://dev-x7eacpbs.us.auth0.com/oauth/token"
	devUrl := "https://dev-x7eacpbs.us.auth0.com/api/v2/"
	payload := strings.NewReader("grant_type=client_credentials&client_id=" + clientId + "&client_secret=" + clientSecret + "&audience=" + devUrl)
	// payload := strings.NewReader("grant_type=client_credentials&client_id=" + c.ClientId + "&client_secret=" + c.ClientSecret + "&audience=" + devUrl)
	fmt.Println("payload ->", payload)
	req, _ := http.NewRequest("POST", url, payload)
	req.Header.Add("content-type", "application/x-www-form-urlencoded")
	// req.Header.Add("authorization", "Bearer "+jwt)
	res, _ := http.DefaultClient.Do(req)
	// defer res.Body.Close()
	body, _ := ioutil.ReadAll(res.Body)
	fmt.Println("body ->", string(body))
	return string(body)
}

func handle(err error) {
	if err != nil {
		log.Fatal(err)
	}
}

type GetResponsesParams struct {
	PageSize int    `url:"page_size"`
	After    string `url:"after,omitempty"`
}

type GetResponsesResponse struct {
	Items []struct {
		Parent_surveyid  string    `json:"parent_surveyid"`
		Token            string    `json:"token"`
		Parent_shortcode string    `json:"parent_shortcode"`
		Surveyid         string    `json:"surveyid"`
		Flowid           string    `json:"flowid"`
		Userid           string    `json:"userid"`
		Question_ref     string    `json:"question_ref"`
		Question_idx     string    `json:"question_idx"`
		Question_text    string    `json:"question_text"`
		Response         string    `json:"response"`
		Timestamp        time.Time `json:"timestamp"`
		Metadata         struct {
			Text string `json:"type"`
		} `json:"Metadata"`
		Pageid              string                     `json:"pageid"`
		Translated_response string                     `json:"translated_response"`
		Hidden              map[string]json.RawMessage `json:"hidden"`
	} `json:"items"`
}

type Answer struct {
	Response            string
	Translated_response string
}

type flyConnector struct {
	BaseUrl  string `env:"FLY_BASE_URL,required"`
	Key      string `env:"FLY_KEY,required"`
	PageSize int    `env:"FLY_PAGE_SIZE,required"`
}

type FlyError struct {
	Code string `json:"code"`
}

func (e *FlyError) Empty() bool {
	return e.Code == ""
}

func (e *FlyError) Error() string {
	return e.Code
}

func (c flyConnector) loadEnv() flyConnector {
	err := env.Parse(&c)
	handle(err)
	return c
}

func Call(client *http.Client, baseUrl string, key string, form string, params *GetResponsesParams) (*GetResponsesResponse, error) {
	sli := sling.New().Client(client).Base(baseUrl).Set("Accept", "application/json").Set("Authorization", fmt.Sprintf("Bearer %s", key))
	res := new(GetResponsesResponse)
	apiError := new(FlyError)

	// fmt.Println("key ->", key)
	// fmt.Println("params ->", params)
	_, err := sli.Get("all?").QueryStruct(params).Receive(res, apiError)
	// fmt.Println("resp: ", resp)
	if err != nil {
		return nil, err
	}

	if !apiError.Empty() {
		return nil, apiError
	}
	return res, nil
}

func (c flyConnector) GetResponses(source *Source, form string, token string, idx int) <-chan *InferenceDataEvent {
	events := make(chan *InferenceDataEvent)
	params := &GetResponsesParams{PageSize: c.PageSize, After: token}
	client := &http.Client{}

	// c.GetToken()
	go func() {
		defer close(events)
		// TODO: for loop to paginate here?
		params.After = token
		for {
			res, err := Call(client, c.BaseUrl, c.Key, form, params)

			if err != nil {
				handle(err)
			}
			for _, item := range res.Items {
				// for pagination
				params.After = item.Token

				md := item.Hidden

				p := Answer{
					Response:            item.Response,
					Translated_response: item.Translated_response,
				}

				datosJson, err := json.Marshal(p)
				if err != nil {
					log.Fatal(err)
				}

				idx++
				event := &InferenceDataEvent{
					User:       User{ID: item.Userid, Metadata: md},
					Study:      source.StudyID,
					SourceConf: source.Conf,
					Timestamp:  item.Timestamp,
					Idx:        idx,
					Pagination: item.Token,
					// Here I am not sure if it is the equivalent
					Variable: item.Question_ref,
					Value:    []byte(datosJson),
				}
				events <- event
			}
			// }

			if len(res.Items) < params.PageSize {
				break
			}

		}
	}()

	return events
}

func (c flyConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	return nil
}

var hmacSampleSecret []byte

func main() {
	c := flyConnector{}
	c.loadEnv()
	connector.LoadEvents(c, "fly", "idx")
	credentials := connector.LoadEventsFlyCredentials(c, "fly", "idx")

	// for i := range credentials {
	// 	fmt.Println(credentials[i])
	// }

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, jwt.MapClaims{
		"user_id": credentials[3].Userid,
		"key":     credentials[3].Key,
		"name":    credentials[3].Details.FirstName,
	})

	// Sign and get the complete encoded token as a string using the secret
	tokenString, err := token.SignedString(hmacSampleSecret)
	fmt.Println(tokenString, err)

	clientId := credentials[4].Userid
	clientSecret := credentials[4].Key

	c.GetToken(clientId, clientSecret)
}