package main

import (
	"database/sql"
	"time"
)

type Project struct {
	ID        string    `json:"id" db:"id"`
	Name      string    `json:"name" db:"name"`
	Version   string    `json:"version" db:"version"`
	CreatedAt time.Time `json:"createdAt" db:"created_at"`
	UpdatedAt time.Time `json:"updatedAt" db:"updated_at"`
}

type Image struct {
	ID        string    `json:"id" db:"id"`
	ProjectID string    `json:"projectId" db:"project_id"`
	Path      string    `json:"path" db:"path"`
	PHash     string    `json:"pHash" db:"phash"`
	CreatedAt time.Time `json:"createdAt" db:"created_at"`
}

type Task struct {
	ID            string         `json:"id" db:"id"`
	ProjectID     string         `json:"projectId" db:"project_id"`
	ImageAID      string         `json:"imageAId" db:"image_a_id"`
	ImageBId      sql.NullString `json:"imageBId" db:"image_b_id"`
	Prompt        sql.NullString `json:"prompt" db:"prompt"`
	Skipped       bool           `json:"skipped" db:"skipped"`
	CandidateBIds []string       `json:"candidateBIds"`
	CreatedAt     time.Time      `json:"createdAt" db:"created_at"`
	UpdatedAt     time.Time      `json:"updatedAt" db:"updated_at"`
}