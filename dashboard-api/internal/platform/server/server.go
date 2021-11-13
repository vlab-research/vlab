package server

import (
	"database/sql"
	"fmt"
	"log"

	"github.com/gin-gonic/gin"
	studiesmanager "github.com/vlab-research/vlab/dashboard-api/internal"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/health"
	"github.com/vlab-research/vlab/dashboard-api/internal/platform/server/handler/studies"
)

type Server struct {
	engine          *gin.Engine
	httpAddr        string
	db              *sql.DB
	studyRepository studiesmanager.StudyRepository
}

func New(host string, port uint, db *sql.DB, studyRepository studiesmanager.StudyRepository) Server {
	srv := Server{
		engine:          gin.New(),
		httpAddr:        fmt.Sprintf("%s:%d", host, port),
		db:              db,
		studyRepository: studyRepository,
	}

	srv.registerRoutes()

	return srv
}

func (s *Server) Run() error {
	log.Println("Server running on", s.httpAddr)
	return s.engine.Run(s.httpAddr)
}

func (s *Server) registerRoutes() {
	s.engine.GET("/health", health.CheckHandler(s.db))
	s.engine.GET("/studies/:slug", studies.ReadHandler(s.studyRepository))
}
