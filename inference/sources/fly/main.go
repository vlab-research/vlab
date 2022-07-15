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
	. "github.com/vlab-research/vlab/inference/inference-data"
)

func (c flyConnector) GetToken() string {
	url := "https://dev-x7eacpbs.us.auth0.com/oauth/token"
	devUrl := "https://dev-x7eacpbs.us.auth0.com/api/v2/"
	payload := strings.NewReader("grant_type=client_credentials&client_id=" + c.ClientId + "&client_secret=" + c.ClientSecret + "&audience=" + devUrl)
	req, _ := http.NewRequest("POST", url, payload)
	req.Header.Add("content-type", "application/x-www-form-urlencoded")
	res, _ := http.DefaultClient.Do(req)
	// defer res.Body.Close()
	body, _ := ioutil.ReadAll(res.Body)
	// fmt.Println("res ->", res)
	// fmt.Println(string(body))
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
	TotalItems int `json:"total_items"`
	PageCount  int `json:"page_count"`
	Items      []struct {
		Parent_surveyid  string `json:"parent_surveyid"`
		Parent_shortcode string `json:"parent_shortcode"`
		Surveyid         string `json:"surveyid"`
		Flowid           string `json:"flowid"`
		Userid           string `json:"userid"`
		Question_ref     string `json:"question_ref"`
		Question_idx     string `json:"question_idx"`
		Question_text    string `json:"question_text"`
		Response         struct {
			Text string `json:"user_agent"`
		} `json:"res"`
		Timestamp time.Time `json:"timestamp"`
		Metadata  struct {
			Text string `json:"type"`
		} `json:"Metadata"`
		Pageid              string                     `json:"pageid"`
		Translated_response string                     `json:"translated_response"`
		Hidden              map[string]json.RawMessage `json:"hidden"`
	} `json:"items"`
}

type flyConnector struct {
	BaseUrl      string `env:"FLY_BASE_URL,required"`
	Key          string `env:"FLY_KEY,required"`
	PageSize     int    `env:"FLY_PAGE_SIZE,required"`
	ClientId     string `env:"FLY_CLIENT_ID,required"`
	ClientSecret string `env:"FLY_CLIENT_SECRET,required"`
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

	// GetTOKEN()
	go func() {
		defer close(events)
		// for loop to paginate here?
		params.After = token
		for {
			res, err := Call(client, c.BaseUrl, c.Key, form, params)

			if err != nil {
				handle(err)
			}
			for _, item := range res.Items {
				md := item.Hidden

				fmt.Printf("response: %v\n \n", item.Surveyid)
				//Todo:  sabe database
				params.After = item.Pageid
				idx++
				event := &InferenceDataEvent{
					User:       User{ID: item.Userid, Metadata: md},
					Study:      source.StudyID,
					SourceConf: source.Conf,
					Timestamp:  item.Timestamp,
					Idx:        idx,
					Pagination: item.Surveyid,
					// Variable:   ??,
					// Value: ??,
				}
				events <- event
			}
			if res.TotalItems == 3 {
				break
			}

		}
	}()

	return events
}

func (c flyConnector) Handler(source *Source, lastEvent *InferenceDataEvent) <-chan *InferenceDataEvent {
	return nil
}

func main() {
	// todo: temporarily  flyConnector
	c :=
		flyConnector{
			BaseUrl:  "https://demo6926047.mockable.io/flys",
			Key:      "parent_shortcode",
			PageSize: 1,
			// GrantType: "client_credentials&client_id=P0F1mNGTyOfAFEvgZEtjRHVBEEmzIyPi&client_secret=TXt1afXrWQitQxfKR4MwSdhPc5puWMiqXrv1Wmx64VluJM-xLgoFYfVa5neVieg5&audience=https://dev-x7eacpbs.us.auth0.com/api/v2/",
		}
	c.loadEnv()
	// cnf := &SourceConf{
	cnf := &SourceConf{
		//         Name:   "",
		Name: "",
		//         Source: "",
		Source: "",
		//         Config: []byte(`foo`),
		Config: []byte(`foo`),
		// }
	}
	// events := c.GetResponses(&Source{"flys", cnf}, "formfoo", "oldtoken", 350)
	events := c.GetResponses(&Source{"flys", cnf}, "formfoo", "oldtoken", 350)
	// fmt.Printf("Fin: %v\n", events)
	fmt.Printf("Fin: %v\n", events)
}
