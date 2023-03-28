package types

import (
	"context"
	"encoding/json"
	"reflect"
	"time"
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
		// as it will just have empty data as well as if it is not one of
		// the confs which should all be pointers
		if field.IsZero() || field.Kind() != reflect.Ptr {
			continue
		}

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
	return res, nil
}

// TransformFromDatabase gets a list of DatabaseStudyConf and iterates
// through it, adding the relevant configs to the StudyConf struct
func (sc *StudyConf) TransformFromDatabase(dcs []*DatabaseStudyConf) error {
	type unmarshalFunc func([]byte, any) error

	unmarshalFuncs := map[string]unmarshalFunc{
		"general":                json.Unmarshal,
		"targeting":              json.Unmarshal,
		"targeting_distribution": json.Unmarshal,
		"recruitment":            json.Unmarshal,
	}

	for _, d := range dcs {
		if unmarshalFunc, ok := unmarshalFuncs[d.ConfType]; ok {
			if err := unmarshalFunc(d.Conf, sc.getConfigValue(d.ConfType)); err != nil {
				return err
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
	case "targeting":
		return &sc.Targeting
	case "targeting_distribution":
		return &sc.TargetingDistribution
	case "recruitment":
		return &sc.Recruitment
	default:
		return nil
	}
}

// GeneralConf is used to hold all general configuration
// for a study
type GeneralConf struct {
	Name             string `json:"name"`
	Objective        string `json:"objective"`
	OptimizationGoal string `json:"optimization_goal"`
	DestinationType  string `json:"destination_type"`
	PageID           string `json:"page_id"`
	MinBudget        int    `json:"min_budget"`
	OptInWindow      int    `json:"opt_window"`
	InstagramID      string `json:"instagram_id"`
	AdAccount        string `json:"ad_account"`
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

// DatabaseStudyConf is the structure used to store data
// in the database
type DatabaseStudyConf struct {
	Created  time.Time
	StudyID  string
	ConfType string
	Conf     json.RawMessage
}
