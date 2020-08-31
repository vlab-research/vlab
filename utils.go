package main

import (
	"fmt"
	"strings"
	"time"
)


func UpsertQuery(table string, fields []string) string {
	placeholders := make([]string, len(fields))
	for i, _ := range fields {
		placeholders[i] = fmt.Sprintf("$%v", i+1)
	}

	query := fmt.Sprintf("UPSERT INTO %v(", table)
	query += strings.Join(fields, ",")
	query += ") VALUES ("
	query += strings.Join(placeholders, ",")
	query += ")"

	return query
}

func ParseTimestamp(timestamp int64) time.Time {
	return time.Unix(0, timestamp*1000000).UTC()
}
