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
}

// StudyConf is the root config that holds the various
// different types of study configuration that can be
// applied to a study that gets sent by the frontend
type StudyConf struct {
	StudyID               string                    `json:"-"`
	UserID                string                    `json:"-"`
	General               GeneralConf               `json:"general"`
	Targeting             TargetingConf             `json:"targeting"`
	TargetingDistribution TargetingDistributionConf `json:"targeting_distribution"`
	// add any new config structs here
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
		// as it will just have empty data
		if field.IsZero() {
			continue
		}

		switch field.Kind() {
		case reflect.Struct, reflect.Slice:
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

// DatabaseStudyConf is the structure used to store data
// in the database
type DatabaseStudyConf struct {
	CreatedAt time.Time
	StudyID   string
	ConfType  string
	Conf      json.RawMessage
}
