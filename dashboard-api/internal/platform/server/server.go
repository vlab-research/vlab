package server

import (
	"fmt"
	"log"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/accounts"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/health"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/segmentsprogress"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/studies"
	studyconf "github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/studyconf"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/users"
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

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowHeaders = []string{"Origin", "Content-Length", "Content-Type", "Authorization"}

	s.Engine.Use(cors.New(config))

	// API for Health Check
	s.Engine.GET("/health", health.CheckHandler(s.repositories, s.auth0Domain))

	//APIS used for the studies resource
	s.Engine.GET("/studies/:slug", s.ensureValidTokenMiddleware, studies.ReadHandler(s.repositories))
	s.Engine.GET("/studies", s.ensureValidTokenMiddleware, studies.ListHandler(s.repositories))
	s.Engine.POST("/studies", s.ensureValidTokenMiddleware, studies.CreateHandler(s.repositories))
	s.Engine.GET("/studies/:slug/segments-progress", s.ensureValidTokenMiddleware, segmentsprogress.ListHandler(s.repositories))

	//APIS for the study configurations resource
	s.Engine.POST("/studies/:slug/conf", s.ensureValidTokenMiddleware, studyconf.CreateHandler(s.repositories))
	s.Engine.GET("/studies/:slug/conf", s.ensureValidTokenMiddleware, studyconf.ReadHandler(s.repositories))

	//APIS for users
	s.Engine.POST("/users", s.ensureValidTokenMiddleware, users.CreateHandler(s.repositories))

	//API for accounts
	s.Engine.POST("/accounts", s.ensureValidTokenMiddleware, accounts.CreateHandler(s.repositories))
}
