package main

import (
	"encoding/json"
	"fmt"
	"strings"
	"time"
)

func SertQuery(sert string, table string, fields []string, values []interface{}) string {
	query := fmt.Sprintf("%v INTO %v(", sert, table)
	query += strings.Join(fields, ",")
	query += ") VALUES "
	query += Placeholders(len(fields), len(values)/len(fields))
	return query
}

func Placeholders(numVals int, numRows int) string {
	rows := make([]string, numRows)
	n := 0
	for i := range rows {
		placeholders := make([]string, numVals)
		for j := range placeholders {
			n += 1
			placeholders[j] = fmt.Sprintf("$%v", n)
		}
		rows[i] = "(" + strings.Join(placeholders, ",") + ")"
	}

	return strings.Join(rows, ",")
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
