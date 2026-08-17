package inference_data

import (
	"encoding/json"
	"time"
)

type User struct {
	ID       string                     `json:"id"`
	Metadata map[string]json.RawMessage `json:"metadata"`
}

type SourceConf struct {
	Name           string          `json:"name"`
	Source         string          `json:"source"`
	Config         json.RawMessage `json:"config"`
	CredentialsKey string          `json:"credentials_key"`
}

type Credentials struct {
	Entity  string          `json:"entity"`
	Key     string          `json:"string"`
	Details json.RawMessage `json:"details"`
	Created time.Time       `json:"created"`
}

type Source struct {
	StudyID     string
	Conf        *SourceConf
	Credentials *Credentials
}

// DB reprsentation of configuration of data sources for a study
type DataSourceConf []*SourceConf

// NetworkFacebook is the ad network every Meta ad belongs to.
//
// This is the *ad* network, not the messaging channel. Messenger ads and
// WhatsApp ads are both Meta ads sharing one id namespace, so both are
// "facebook". Mapping WhatsApp to a "whatsapp" network is the easy mistake and
// an expensive one: ad_attributions is keyed (network, ad_id), so a wrong
// network here makes every lookup miss — and a miss is not an error, it is a
// respondent attributed to no stratum.
const NetworkFacebook = "facebook"

type InferenceDataEvent struct {
	User       User            `json:"user"`
	Study      string          `json:"study"`
	SourceConf *SourceConf     `json:"source_conf"`
	Timestamp  time.Time       `json:"timestamp"`
	Variable   string          `json:"variable"`
	Value      json.RawMessage `json:"value"`
	Idx        int             `json:"idx"`
	Pagination string          `json:"pagination"`

	// AdID is the opaque identifier of the ad that recruited this respondent,
	// carried through unchanged from whatever the source platform reported.
	// Empty means the respondent arrived organically — no ad — which is an
	// expected outcome, not a failure.
	//
	// AdNetwork is the namespace AdID lives in, supplied by the connector to
	// match ad_attributions' key. See NetworkFacebook.
	//
	// These are first-class typed fields rather than reserved keys inside
	// User.Metadata deliberately. A map key would be a fly-shaped convention
	// that every future connector has to imitate with nothing enforcing it —
	// the same shape of mistake as the dotted ref, which was a convention
	// smuggled inside an untyped blob. The field is the contract; each source
	// works out how to meet it.
	//
	// omitempty keeps the persisted shape of non-ad events byte-identical to
	// what it was before these fields existed. inference_data_events stores the
	// whole event as one JSON blob (`data`), so this needs no migration.
	AdID      string `json:"ad_id,omitempty"`
	AdNetwork string `json:"ad_network,omitempty"`
}

type InferenceDataValue struct {
	Timestamp time.Time       `json:"timestamp"`
	Variable  string          `json:"variable"`
	Value     json.RawMessage `json:"value"`
	ValueType string          `json:"value_type"`
}

type InferenceDataRow struct {
	User string                         `json:"user"`
	Data map[string]*InferenceDataValue `json:"data"`
}

type InferenceData map[string]*InferenceDataRow

type IntermediateInferenceData map[string]InferenceData
