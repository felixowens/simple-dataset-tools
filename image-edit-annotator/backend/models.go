package main

type Project struct {
	ID      string `json:"id"`
	Name    string `json:"name"`
	Version string `json:"version"`
}

type Image struct {
	ID        string `json:"id"`
	ProjectID string `json:"projectId"`
	Path      string `json:"path"`
	PHash     string `json:"pHash"`
}

type Task struct {
	ID          string   `json:"id"`
	ProjectID   string   `json:"projectId"`
	ImageAID    string   `json:"imageAId"`
	ImageBId    string   `json:"imageBId"`
	Prompt      string   `json:"prompt"`
	Skipped     bool     `json:"skipped"`
	CandidateBIds []string `json:"candidateBIds"`
}