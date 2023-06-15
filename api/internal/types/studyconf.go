package types

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"reflect"
	"time"

	"github.com/tidwall/gjson"
)

type DistributionVar string

const (
	Location DistributionVar = "location"
	Gender   DistributionVar = "gender"
	Age      DistributionVar = "age"
)

type StudyConfRepository interface {
	Create(ctx context.Context, dsc DatabaseStudyConf) error
	GetByStudySlug(
		ctx context.Context,
		slug, userID string,
	) ([]*DatabaseStudyConf, error)
}

// StudyConf is the root config that holds the various
// different types of study configuration that can be
// applied to a study that gets sent by the frontend
type StudyConf struct {
	StudyID               string                     `json:"-"`
	UserID                string                     `json:"-"`
	General               *GeneralConf               `json:"general"`
	Targeting             *TargetingConf             `json:"targeting"`
	TargetingDistribution *TargetingDistributionConf `json:"targeting_distribution"`
	Recruitment           *RecruitmentConf           `json:"recruitment"`
	Destinations          *DestinationConf           `json:"destinations"`
	Creatives             []*CreativeConf            `json:"creatives"`
	Audiences             []*AudienceConf            `json:"audiences"`
	Strata                []*StratumConf             `json:"strata"`
	// add any new config structs here
	// NOTE: Confs should be pointers as this allows JSON unmarshalling
	// to null if they are not set
}

// TransformForDatabase will take the StudyConfig that is passed from the
// frontend and transform it into a list that will be accepted by the database
// This is a Generic implementation as we have various types of configs that
// require the same transform to be done.
func (sc *StudyConf) TransformForDatabase() (res []DatabaseStudyConf, err error) {
	studyID := sc.StudyID
	v := reflect.ValueOf(*sc)
	// we iterate through each field of the struct
	for i := 0; i < v.NumField(); i++ {
		// this is how we get the value of the config
		field := v.Field(i)
		// we use the JSON tag as that is what the  adopt
		// service use to identify the config
		fieldName := v.Type().Field(i).Tag.Get("json")
		// if a field is not set we dont need to add it to our array
		if field.IsZero() {
			continue
		}
		// confs should all be pointers or slices
		if field.Kind() == reflect.Ptr || field.Kind() == reflect.Slice {
			// we marshal the full config to json to be stored
			conf, err := json.Marshal(field.Interface())
			if err != nil {
				return nil, err
			}
			res = append(res, DatabaseStudyConf{
				StudyID:  studyID,
				ConfType: fieldName,
				Conf:     conf,
			})
		}
	}
	return res, nil
}

// TransformFromDatabase gets a list of DatabaseStudyConf and iterates
// through it, adding the relevant configs to the StudyConf struct
func (sc *StudyConf) TransformFromDatabase(dcs []*DatabaseStudyConf) error {
	type unmarshalFunc func([]byte, any) error

	unmarshalFuncs := map[string]unmarshalFunc{
		"general":                json.Unmarshal,
		"creatives":              json.Unmarshal,
		"targeting":              json.Unmarshal,
		"targeting_distribution": json.Unmarshal,
		"recruitment":            json.Unmarshal,
		"destinations":           json.Unmarshal,
		"audiences":              json.Unmarshal,
		"strata":                 json.Unmarshal,
	}

	errMsg := "there was an error fetching the %s configuration"
	for _, d := range dcs {
		if unmarshalFunc, ok := unmarshalFuncs[d.ConfType]; ok {
			if err := unmarshalFunc(d.Conf, sc.getConfigValue(d.ConfType)); err != nil {
				return fmt.Errorf(errMsg, d.ConfType)
			}
		}
	}

	return nil
}

// getConfigValue uses the config json string to the relevant pointer
func (sc *StudyConf) getConfigValue(confType string) interface{} {
	switch confType {
	case "general":
		return &sc.General
	case "destinations":
		return &sc.Destinations
	case "creatives":
		return &sc.Creatives
	case "targeting":
		return &sc.Targeting
	case "targeting_distribution":
		return &sc.TargetingDistribution
	case "recruitment":
		return &sc.Recruitment
	case "audiences":
		return &sc.Audiences
	case "strata":
		return &sc.Strata
	default:
		return nil
	}
}

// GeneralConf is used to hold all general configuration
// for a study
type GeneralConf struct {
	Name             string  `json:"name"`
	Objective        string  `json:"objective"`
	OptimizationGoal string  `json:"optimization_goal"`
	DestinationType  string  `json:"destination_type"`
	PageID           string  `json:"page_id"`
	MinBudget        float32 `json:"min_budget"`
	OptInWindow      int     `json:"opt_window"`
	InstagramID      string  `json:"instagram_id"`
	AdAccount        string  `json:"ad_account"`
}

// TargetingConf describes the variables for stratification and the
// desired joint distribution of respondents.
type TargetingConf struct {
	TemplateCampaignName string          `json:"template_campaign_name"`
	DistributionVars     DistributionVar `json:"distribution_vars"`
}

// TargetingDistributionConf proportion of people do you want in
// your final sample from each stratum
type TargetingDistributionConf struct {
	//TODO verify if age should be a string
	Age      string `json:"age"`
	Gender   string `json:"gender"`
	Location string `json:"location"`
}

// Recruitment is the configuration used to work with the facebook campaign
type RecruitmentConf struct {
	// Common Fields
	// These are set to strings as they are in the following format
	// 2022-08-05T00:00:00
	// Which is none standard in Golang and makes it cumbersome to
	// unmarshall to time.Time. We have no need for them to be
	// unmarshalled for now
	EndDate   string `json:"end_date"`
	StartDate string `json:"start_date"`

	// Simple Recruitment Fields
	AdCampaignName string `json:"ad_campaign_name,omitempty"`
	Budget         int    `json:"budget,omitempty"`
	MaxSample      int    `json:"max_sample,omitempty"`

	// Experiment Recruitment Fields
	Arms            int `json:"arms,omitempty"`
	RecruitmentDays int `json:"recruitment_days,omitempty"`
	OffsetDays      int `json:"offset_days,omitempty"`

	//Destination Recruitment Fields
	Destinations []string `json:"destinations,omitempty"`

	//Common Destination and Experiment Fields
	AdCampaignNameBase string `json:"ad_campaign_name_base,omitempty"`
	BudgetPerArm       int    `json:"budget_per_arm,omitempty"`
	MaxSamplePerArm    int    `json:"max_sample_per_arm,omitempty"`
}

// Destination is where to send a recruitee to
// we use a blank interface as it could be different types
type Destination interface{}

// DestinationConf as we have multiple types of destination
type DestinationConf []Destination

// UnmarshalJSON is a custom unmarshaller to handle the different types
// of destinations
func (d *DestinationConf) UnmarshalJSON(data []byte) error {
	dests := []Destination{}
	for _, item := range gjson.Parse(string(data)).Array() {
		switch {
		//WebDestination should always have URLTemplate
		//set
		case item.Get("url_template").Exists():
			d := &WebDestination{}
			if err := json.Unmarshal([]byte(item.Raw), d); err != nil {
				return err
			}
			d.Type = "web"
			dests = append(dests, d)
		//FlyDestination should always have InitialShortcode
		//set
		case item.Get("initial_shortcode").Exists():
			d := &FlyDestination{}
			if err := json.Unmarshal([]byte(item.Raw), d); err != nil {
				return err
			}
			d.Type = "messenger"
			dests = append(dests, d)
		//AppDestination should always have FacebookAppID
		case item.Get("facebook_app_id").Exists():
			d := &AppDestination{}
			if err := json.Unmarshal([]byte(item.Raw), d); err != nil {
				return err
			}
			d.Type = "app"
			dests = append(dests, d)
		default:
			return errors.New("invalid destination found when unmarshalling")
		}
	}
	*d = dests
	return nil
}

// WebDestination is a destination that you can pass a url to
// in order to redirect users to a specific survey platform
type WebDestination struct {
	Type        string `json:"type"`
	Name        string `json:"name"`
	URLTemplate string `json:"url_template"`
}

// FlyDestination is used to direct users to the Fly survey
type FlyDestination struct {
	Type             string `json:"type"`
	Name             string `json:"name"`
	InitialShortcode string `json:"initial_shortcode"`
}

// AppDestination
type AppDestination struct {
	Type             string   `json:"type"`
	Name             string   `json:"name"`
	FacebookAppID    string   `json:"facebook_app_id"`
	AppInstallLink   string   `json:"app_install_link"`
	DeeplinkTemplate string   `json:"deeplink_template"`
	AppInstallState  string   `json:"app_install_state"`
	UserDevice       []string `json:"user_device"`
	UserOS           []string `json:"user_os"`
}

// CreativeConf these are essential fields that relate to an ad
// and link to a destination
type CreativeConf struct {
	Body           string   `json:"body"`
	ButtonText     string   `json:"button_text"`
	Destination    string   `json:"destination"`
	ImageHash      string   `json:"image_hash"`
	LinkText       string   `json:"link_text"`
	Name           string   `json:"name"`
	WelcomeMessage string   `json:"welcome_message"`
	Tags           []string `json:"tags"`
}

// AudienceConf is how the audience is configured for the
// study
type AudienceConf struct {
	Name              string             `json:"name"`
	SubType           string             `json:"subtype"`
	Lookalike         *Lookalike         `json:"lookalike,omitempty"`
	QuestionTargeting *QuestionTargeting `json:"question_targeting,omitempty"`
	Partioning        *Partioning        `json:"partioning,omitempty"`
}

// QuestionTargeting is set as an interface as it allows for a
// nested type structure with various types
// we use map[string]interface{} as we should be dealing with json
type QuestionTargeting map[string]interface{}

// Lookalike is reflective of the lookalike capabilities in
// facebook ads
type Lookalike struct {
	Target int           `json:"target"`
	Spec   LookalikeSpec `json:"spec"`
}

// LookalikeSpec is the specifications used in a lookalike
type LookalikeSpec struct {
	Country       string  `json:"country"`
	Ratio         float64 `json:"ratio"`
	StartingRatio float64 `json:"starting_ratio"`
}

// Partioning
type Partioning struct {
	MinUsers *int `json:"min_users"`
	MinDays  *int `json:"min_days,omitempty"`
	MaxDays  *int `json:"max_days,omitempty"`
	MaxUsers *int `json:"max_users,omitempty"`
}

// StratumConf is groups that we divide our targeting groups into
type StratumConf struct {
	ID                string             `json:"id"`
	Quota             float64            `json:"quota"`
	Audiences         []string           `json:"audiences"`
	ExcludedAudiences []string           `json:"excluded_audiences"`
	Creatives         []string           `json:"creatives"`
	FacebookTargeting *FacebookTargeting `json:"facebook_targeting"`
	QuestionTargeting *QuestionTargeting `json:"question_targeting,omitempty"`
	Metadata          *Metadata          `json:"metadata"`
}

// FacebookTargeting
type FacebookTargeting map[string]interface{}

// Metadata used to keep instance information
type Metadata map[string]string

// DatabaseStudyConf is the structure used to store data
// in the database
type DatabaseStudyConf struct {
	Created  time.Time
	StudyID  string
	ConfType string
	Conf     json.RawMessage
}
