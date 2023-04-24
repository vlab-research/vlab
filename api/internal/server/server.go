package server

import (
	"fmt"
	"net/http"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	fb "github.com/huandu/facebook/v2"
	"github.com/vlab-research/vlab/dashboard-api/internal/config"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/accounts"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/facebook"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/health"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/segmentsprogress"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/studies"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/studyconf"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/handler/users"
	"github.com/vlab-research/vlab/dashboard-api/internal/server/middleware/auth"
	"github.com/vlab-research/vlab/dashboard-api/internal/storage"
)

type Server struct {
	// We embed an http server
	http.Server

	Cfg            *config.Config
	httpAddr       string
	Repos          storage.Repositories
	FacebookApp    *fb.App
	AuthMiddleware gin.HandlerFunc
}

// New creates a new instance of the api server
func New(cfg *config.Config) Server {
	//Setup facebook app
	fbApp := fb.New(cfg.Facebook.ClientID, cfg.Facebook.ClientSecret)
	fbApp.RedirectUri = cfg.Facebook.RedirectURI

	srv := Server{
		Cfg:         cfg,
		FacebookApp: fbApp,
		Repos:       storage.InitializeRepositories(cfg.DB),
		AuthMiddleware: auth.EnsureValidTokenMiddleware(
			cfg.Auth0.Domain,
			cfg.Auth0.Audience,
		),
	}
	srv.GetRouter()

	return srv
}

func (s *Server) GetRouter() {
	r := gin.Default()

	config := cors.DefaultConfig()
	config.AllowAllOrigins = true
	config.AllowHeaders = []string{"Origin", "Content-Length", "Content-Type", "Authorization"}
	r.Use(cors.New(config))

	// API for Health Check
	r.GET("/health", health.CheckHandler(s.Repos, s.Cfg.Auth0.Domain))

	//APIS used for the studies resource
	r.GET("/studies/:slug", s.AuthMiddleware, studies.ReadHandler(s.Repos))
	r.GET("/studies", s.AuthMiddleware, studies.ListHandler(s.Repos))
	r.POST("/studies", s.AuthMiddleware, studies.CreateHandler(s.Repos))
	r.GET("/studies/:slug/segments-progress", s.AuthMiddleware, segmentsprogress.ListHandler(s.Repos))

	//APIS for the study configurations resource
	r.POST("/studies/:slug/conf", s.AuthMiddleware, studyconf.CreateHandler(s.Repos))
	r.GET("/studies/:slug/conf", s.AuthMiddleware, studyconf.ReadHandler(s.Repos))

	//APIS for users
	r.POST("/users", s.AuthMiddleware, users.GetOrCreateHandler(s.Repos))

	//API for accounts
	r.POST("/accounts", s.AuthMiddleware, accounts.CreateHandler(s.Repos))
	r.GET("/accounts", s.AuthMiddleware, accounts.ListHandler(s.Repos))
	r.DELETE("/accounts", s.AuthMiddleware, accounts.DeleteHandler(s.Repos))

	//API for facebook connections
	r.POST("/facebook/token", s.AuthMiddleware, facebook.GenerateToken(s.FacebookApp, s.Repos))

	// Add router to server
	s.Handler = r
	s.Addr = fmt.Sprintf("%s:%d", s.Cfg.Host, s.Cfg.Port)

}
