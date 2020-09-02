package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)


func SertQuery(sert string, table string, fields []string) string {
	placeholders := make([]string, len(fields))
	for i, _ := range fields {
		placeholders[i] = fmt.Sprintf("$%v", i+1)
	}

	query := fmt.Sprintf("%v INTO %v(", sert, table)
	query += strings.Join(fields, ",")
	query += ") VALUES ("
	query += strings.Join(placeholders, ",")
	query += ")"

	return query
}

type JSTimestamp struct {
	time.Time 
}

func (t *JSTimestamp) UnmarshalJSON(b []byte) error {
	var i int64
	err := json.Unmarshal(b, &i)
	if err != nil {
		return err
	}
	*t = JSTimestamp{time.Unix(0, i*1000000).UTC()}
	return nil
}


type CastString struct {
	String string
}

func (f *CastString) UnmarshalJSON(b []byte) error {
	// response can be string, but also boolean or number
	// but we store it in the database as a string always
	var s string
	err := json.Unmarshal(b, &s)
	if err == nil {
		*f = CastString{s}
		return nil
	}
	*f = CastString{string(b)}
	return nil
}
