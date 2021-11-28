package server

import (
	"fmt"
	"log"

	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/health"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/segmentsprogress"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/studies"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/storage"
)

type Server struct {
	Engine                     *gin.Engine
	httpAddr                   string
	repositories               storage.Repositories
	ensureValidTokenMiddleware gin.HandlerFunc
	auth0Domain                string
}

func New(
	host string,
	port uint,
	repositories storage.Repositories,
	ensureValidTokenMiddleware gin.HandlerFunc,
	auth0Domain string,
) Server {
	srv := Server{
		Engine:                     gin.New(),
		httpAddr:                   fmt.Sprintf("%s:%d", host, port),
		repositories:               repositories,
		ensureValidTokenMiddleware: ensureValidTokenMiddleware,
		auth0Domain:                auth0Domain,
	}

	srv.registerRoutes()

	return srv
}

func (s *Server) Run() error {
	log.Println("Server running on", s.httpAddr)
	return s.Engine.Run(s.httpAddr)
}

func (s *Server) registerRoutes() {
	s.Engine.GET("/health", health.CheckHandler(s.repositories, s.auth0Domain))

	s.Engine.GET("/studies/:slug", s.ensureValidTokenMiddleware, studies.ReadHandler(s.repositories))
	s.Engine.GET("/studies", s.ensureValidTokenMiddleware, studies.ListHandler(s.repositories))

	s.Engine.GET("/studies/:slug/segments-progress", s.ensureValidTokenMiddleware, segmentsprogress.ListHandler(s.repositories))
}
