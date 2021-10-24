package main

import (
	"log"

	"github.com/vlab-research/vlab/dashboard-api/cmd/api/bootstrap"
)

func main() {
	if err := bootstrap.Run(); err != nil {
		log.Fatal(err)
	}
}
