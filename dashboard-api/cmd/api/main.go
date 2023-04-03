package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/vlab-research/vlab/dashboard-api/internal/config"
	"github.com/vlab-research/vlab/dashboard-api/internal/server"
)

func main() {
	// Termination Handeling
	termChan := make(chan os.Signal, 1)
	signal.Notify(termChan, syscall.SIGINT, syscall.SIGTERM)

	cfg, err := config.Setup()
	if err != nil {
		log.Fatalf("failed loading configurations: %v", err)
	}

	srv := server.New(cfg)
	go func() {
		if err := srv.Run(); err != nil && err != http.ErrServerClosed {
			log.Fatal("Server Start Fail")
		}
	}()

	<-termChan
	// Any Code to Gracefully Shutdown should be done here
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer func() {
		cancel()
	}()
	if err := srv.Engine.Shutdown(ctx); err != nil {
		log.Fatal("Graceful Shutdown Failed")
	}
	log.Info("Shutting Down Gracefully")

}
