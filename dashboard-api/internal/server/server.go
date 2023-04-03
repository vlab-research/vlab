package server

import (
	"fmt"
	"log"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/vlab-research/vlab/dashboard-api/internal/config"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/accounts"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/health"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/segmentsprogress"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/studies"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/studyconf"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/users"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
)

type Server struct {
	Cfg                        *config.Config
	Engine                     *gin.Engine
	httpAddr                   string
	repositories               storage.Repositories
	ensureValidTokenMiddleware gin.HandlerFunc
}

// New creates a new instance of the api server
func New(cfg *config.Config) Server {
	r := storage.InitializeRepositories(cfg.DB)
	authMiddleware := auth.EnsureValidTokenMiddleware(
		cfg.Auth0.Domain,
		cfg.Auth0.Audience,
	)

	srv := Server{
		Cfg:                        cfg,
		Engine:                     gin.New(),
		httpAddr:                   fmt.Sprintf("%s:%d", cfg.Host, cfg.Port),
		repositories:               r,
		ensureValidTokenMiddleware: authMiddleware,
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
	s.Engine.GET("/health", health.CheckHandler(s.repositories, s.Cfg.Auth0.Domain))

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
