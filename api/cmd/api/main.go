package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/vlab-research/vlab/api/internal/config"
	"github.com/vlab-research/vlab/api/internal/server"
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
		log.Printf("running server on %v", srv.Addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("listen: %s\n", err)
		}
	}()

	<-termChan
	// Graceful shutdown, when a SIGTERM is recieved for shutdown it will
	// run the following code which will gracefully stop all connections
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Fatal("Graceful Shutdown Failed")
	}
	// catching ctx.Done(). timeout of 5 seconds.
	select {
	case <-ctx.Done():
		log.Println("timeout of 5 seconds.")
	}
	log.Print("Shutting Down Gracefully")

}
