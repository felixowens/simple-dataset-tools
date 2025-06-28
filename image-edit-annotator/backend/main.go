package main

import (
	"database/sql"
	"encoding/json"
	"fmt"
	"image"
	"io"
	"log/slog"
	"mime/multipart"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"github.com/corona10/goimagehash"
	"github.com/google/uuid"

	_ "image/jpeg"
	_ "image/png"
)

var (
	progressClients = make(map[string]chan ProgressUpdate)
	progressMu      sync.RWMutex
)

type ProgressUpdate struct {
	ProjectID    string `json:"projectId"`
	Filename     string `json:"filename"`
	Progress     int    `json:"progress"`
	Total        int    `json:"total"`
	Status       string `json:"status"`
	ErrorMessage string `json:"errorMessage,omitempty"`
}

func pingHandler(w http.ResponseWriter, r *http.Request) {
	fmt.Fprintf(w, "pong")
}

func createProjectHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var project Project
	if err := json.NewDecoder(r.Body).Decode(&project); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	project.ID = uuid.New().String()

	if err := createProject(&project); err != nil {
		http.Error(w, "Failed to create project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to create project", err, slog.String("project_name", project.Name))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(project)
}

func getProjectHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id := r.URL.Path[len("/projects/"):]
	if id == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	project, err := getProject(id)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project", err, slog.String("project_id", id))
		return
	}

	if project == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(project)
}

func listProjectsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projects, err := listProjects()
	if err != nil {
		http.Error(w, "Failed to list projects", http.StatusInternalServerError)
		logError(r.Context(), "Failed to list projects", err)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(projects)
}

func updateProjectHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPut {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id := r.URL.Path[len("/projects/"):]
	if id == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	var updatedProject Project
	if err := json.NewDecoder(r.Body).Decode(&updatedProject); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	updatedProject.ID = id // Ensure the ID from the URL is used

	// Check if project exists
	existingProject, err := getProject(id)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for update", err, slog.String("project_id", id))
		return
	}
	if existingProject == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	if err := updateProject(&updatedProject); err != nil {
		http.Error(w, "Failed to update project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to update project", err, slog.String("project_id", id))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(updatedProject)
}

func deleteProjectHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	id := r.URL.Path[len("/projects/"):]
	if id == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Check if project exists
	existingProject, err := getProject(id)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for deletion", err, slog.String("project_id", id))
		return
	}
	if existingProject == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	if err := deleteProject(id); err != nil {
		http.Error(w, "Failed to delete project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to delete project", err, slog.String("project_id", id))
		return
	}

	w.WriteHeader(http.StatusNoContent)
}

func uploadHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projectID := r.URL.Query().Get("projectId")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Check if project exists
	project, err := getProject(projectID)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for upload", err, slog.String("project_id", projectID))
		return
	}
	if project == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	// Parse multipart form
	err = r.ParseMultipartForm(32 << 20) // 32MB max memory
	if err != nil {
		http.Error(w, "Error parsing multipart form", http.StatusBadRequest)
		return
	}

	files := r.MultipartForm.File["files"]
	if len(files) == 0 {
		http.Error(w, "No files provided", http.StatusBadRequest)
		return
	}

	// Create project directory
	projectDir := filepath.Join("data", "projects", projectID, "images")
	err = os.MkdirAll(projectDir, 0755)
	if err != nil {
		http.Error(w, "Error creating project directory", http.StatusInternalServerError)
		return
	}

	// Process files asynchronously
	logInfo(r.Context(), "Upload started", 
		slog.String("project_id", projectID),
		slog.Int("file_count", len(files)),
	)
	go processUploadedFiles(projectID, files, projectDir)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"message": "Upload started",
		"count":   len(files),
	})
}

func processUploadedFiles(projectID string, files []*multipart.FileHeader, projectDir string) {
	total := len(files)
	processedImages := make([]Image, 0, total)

	for i, fileHeader := range files {
		// Send progress update
		sendProgressUpdate(projectID, ProgressUpdate{
			ProjectID: projectID,
			Filename:  fileHeader.Filename,
			Progress:  i + 1,
			Total:     total,
			Status:    "processing",
		})

		// Open uploaded file
		file, err := fileHeader.Open()
		if err != nil {
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Filename:     fileHeader.Filename,
				Progress:     i + 1,
				Total:        total,
				Status:       "error",
				ErrorMessage: fmt.Sprintf("Error opening file: %v", err),
			})
			continue
		}

		// Read file content
		content, err := io.ReadAll(file)
		file.Close()
		if err != nil {
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Filename:     fileHeader.Filename,
				Progress:     i + 1,
				Total:        total,
				Status:       "error",
				ErrorMessage: fmt.Sprintf("Error reading file: %v", err),
			})
			continue
		}

		// Validate image
		reader := strings.NewReader(string(content))
		img, _, err := image.Decode(reader)
		if err != nil {
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Filename:     fileHeader.Filename,
				Progress:     i + 1,
				Total:        total,
				Status:       "error",
				ErrorMessage: fmt.Sprintf("Invalid image format: %v", err),
			})
			continue
		}

		// Save file to disk
		filename := fileHeader.Filename
		filePath := filepath.Join(projectDir, filename)
		destFile, err := os.Create(filePath)
		if err != nil {
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Filename:     fileHeader.Filename,
				Progress:     i + 1,
				Total:        total,
				Status:       "error",
				ErrorMessage: fmt.Sprintf("Error creating file: %v", err),
			})
			continue
		}

		_, err = destFile.Write(content)
		destFile.Close()
		if err != nil {
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Filename:     fileHeader.Filename,
				Progress:     i + 1,
				Total:        total,
				Status:       "error",
				ErrorMessage: fmt.Sprintf("Error writing file: %v", err),
			})
			continue
		}

		// Compute pHash
		hash, err := goimagehash.PerceptionHash(img)
		if err != nil {
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Filename:     fileHeader.Filename,
				Progress:     i + 1,
				Total:        total,
				Status:       "error",
				ErrorMessage: fmt.Sprintf("Error computing hash: %v", err),
			})
			continue
		}

		// Create image record
		imageRecord := Image{
			ID:        uuid.New().String(),
			ProjectID: projectID,
			Path:      filepath.Join("images", filename),
			PHash:     hash.ToString(),
		}

		processedImages = append(processedImages, imageRecord)
	}

	// Store images in database
	if len(processedImages) > 0 {
		if err := createImages(processedImages); err != nil {
			logger.Error("Error storing images in database", 
				"error", err,
				"project_id", projectID,
				"image_count", len(processedImages),
			)
			sendProgressUpdate(projectID, ProgressUpdate{
				ProjectID:    projectID,
				Progress:     total,
				Total:        total,
				Status:       "error",
				ErrorMessage: "Failed to store images in database",
			})
			return
		}
		logger.Info("Images stored successfully",
			"project_id", projectID,
			"image_count", len(processedImages),
		)
	}

	// Send completion update
	sendProgressUpdate(projectID, ProgressUpdate{
		ProjectID: projectID,
		Progress:  total,
		Total:     total,
		Status:    "completed",
	})
}

func sendProgressUpdate(projectID string, update ProgressUpdate) {
	progressMu.RLock()
	client, exists := progressClients[projectID]
	progressMu.RUnlock()

	if exists {
		select {
		case client <- update:
		default:
			// Client channel is full, skip this update
		}
	}
}

func progressHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projectID := r.URL.Query().Get("projectId")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Set headers for SSE
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	// Create progress channel for this client
	progressCh := make(chan ProgressUpdate, 100)
	progressMu.Lock()
	progressClients[projectID] = progressCh
	progressMu.Unlock()

	// Clean up when client disconnects
	defer func() {
		progressMu.Lock()
		delete(progressClients, projectID)
		progressMu.Unlock()
		close(progressCh)
	}()

	// Send events to client
	for {
		select {
		case update := <-progressCh:
			data, _ := json.Marshal(update)
			fmt.Fprintf(w, "data: %s\n\n", data)
			w.(http.Flusher).Flush()
		case <-r.Context().Done():
			return
		}
	}
}

func getImagesHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projectID := r.URL.Query().Get("projectId")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	projectImages, err := getImagesByProjectID(projectID)
	if err != nil {
		http.Error(w, "Failed to get images", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get images", err, slog.String("project_id", projectID))
		return
	}

	if projectImages == nil {
		projectImages = []Image{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(projectImages)
}

type SimilarImage struct {
	Image    Image
	Distance int
}

type TaskGenerationRequest struct {
	SimilarityThreshold int `json:"similarityThreshold"`
	MaxCandidates       int `json:"maxCandidates"`
}

type TaskGenerationResponse struct {
	TasksCreated      int     `json:"tasksCreated"`
	AverageCandidates float64 `json:"averageCandidates"`
}

func parseImageHash(hashString string) (*goimagehash.ImageHash, error) {
	return goimagehash.ImageHashFromString(hashString)
}

func findSimilarImages(targetImage Image, allImages []Image, threshold int) ([]SimilarImage, error) {
	targetHash, err := parseImageHash(targetImage.PHash)
	if err != nil {
		return nil, fmt.Errorf("failed to parse target hash: %v", err)
	}

	var similar []SimilarImage
	for _, img := range allImages {
		if img.ID == targetImage.ID {
			continue
		}

		imgHash, err := parseImageHash(img.PHash)
		if err != nil {
			logger.Warn("Failed to parse image hash", 
				"error", err,
				"image_id", img.ID,
			)
			continue
		}

		distance, err := targetHash.Distance(imgHash)
		if err != nil {
			logger.Warn("Failed to calculate image distance", 
				"error", err,
				"image_id", img.ID,
			)
			continue
		}

		logger.Debug("Image distance calculated", 
			"image_id", img.ID,
			"distance", distance,
		)

		if distance <= threshold {
			similar = append(similar, SimilarImage{
				Image:    img,
				Distance: distance,
			})
		}
	}

	// Sort by distance (most similar first)
	for i := 0; i < len(similar)-1; i++ {
		for j := i + 1; j < len(similar); j++ {
			if similar[i].Distance > similar[j].Distance {
				similar[i], similar[j] = similar[j], similar[i]
			}
		}
	}

	return similar, nil
}

func generateTasksForProject(projectID string, threshold, maxCandidates int) (*TaskGenerationResponse, error) {
	images, err := getImagesByProjectID(projectID)
	if err != nil {
		return nil, fmt.Errorf("failed to get images: %v", err)
	}

	if len(images) == 0 {
		return &TaskGenerationResponse{TasksCreated: 0, AverageCandidates: 0}, nil
	}

	var totalCandidates int
	for _, img := range images {
		similarImages, err := findSimilarImages(img, images, threshold)
		if err != nil {
			logger.Warn("Error finding similar images", 
				"error", err,
				"image_id", img.ID,
			)
			continue
		}

		// Limit candidates
		candidates := similarImages
		if len(candidates) > maxCandidates {
			candidates = candidates[:maxCandidates]
		}

		// Extract candidate IDs
		var candidateIDs []string
		for _, candidate := range candidates {
			candidateIDs = append(candidateIDs, candidate.Image.ID)
		}

		// Create task
		task := &Task{
			ID:            uuid.New().String(),
			ProjectID:     projectID,
			ImageAID:      img.ID,
			ImageBId:      sql.NullString{}, // Will be set during annotation
			Prompt:        sql.NullString{}, // Will be set during annotation
			Skipped:       false,
			CandidateBIds: candidateIDs,
		}

		logger.Debug("Creating task", 
			"task_id", task.ID,
			"project_id", projectID,
			"image_id", img.ID,
			"candidate_count", len(candidateIDs),
		)
		if err := createTask(task); err != nil {
			logger.Error("Error creating task", 
				"error", err,
				"task_id", task.ID,
				"project_id", projectID,
				"image_id", img.ID,
			)
			continue
		}

		totalCandidates += len(candidateIDs)
	}

	averageCandidates := float64(totalCandidates) / float64(len(images))
	return &TaskGenerationResponse{
		TasksCreated:      len(images),
		AverageCandidates: averageCandidates,
	}, nil
}

func generateTasksHandler(w http.ResponseWriter, r *http.Request) {
	projectID := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/projects/"), "/generate-tasks")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Check if project exists
	project, err := getProject(projectID)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for task generation", err, slog.String("project_id", projectID))
		return
	}
	if project == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	// Parse request body
	var req TaskGenerationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		// Use defaults if parsing fails
		req.SimilarityThreshold = 10
		req.MaxCandidates = 5
	}

	// Validate parameters
	if req.SimilarityThreshold <= 0 {
		req.SimilarityThreshold = 10
	}
	if req.MaxCandidates <= 0 {
		req.MaxCandidates = 5
	}

	// Generate tasks
	logInfo(r.Context(), "Generating tasks", 
		slog.String("project_id", projectID),
		slog.Int("similarity_threshold", req.SimilarityThreshold),
		slog.Int("max_candidates", req.MaxCandidates),
	)
	response, err := generateTasksForProject(projectID, req.SimilarityThreshold, req.MaxCandidates)
	if err != nil {
		http.Error(w, "Failed to generate tasks", http.StatusInternalServerError)
		logError(r.Context(), "Failed to generate tasks", err, slog.String("project_id", projectID))
		return
	}
	logInfo(r.Context(), "Tasks generated successfully", 
		slog.String("project_id", projectID),
		slog.Int("tasks_created", response.TasksCreated),
		slog.Float64("average_candidates", response.AverageCandidates),
	)

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func corsMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*") // Allow all origins for now
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next.ServeHTTP(w, r)
	})
}

func main() {
	// Initialize logger
	if err := initLogger(); err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}

	// Initialize database
	if err := initDatabase(); err != nil {
		logger.Error("Failed to initialize database", "error", err)
		os.Exit(1)
	}
	defer closeDatabase()

	mux := http.NewServeMux()
	mux.HandleFunc("/ping", pingHandler)
	mux.HandleFunc("/projects", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodPost:
			createProjectHandler(w, r)
		case http.MethodGet:
			listProjectsHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
	mux.HandleFunc("/projects/", func(w http.ResponseWriter, r *http.Request) {
		if strings.HasSuffix(r.URL.Path, "/generate-tasks") && r.Method == http.MethodPost {
			generateTasksHandler(w, r)
			return
		}
		switch r.Method {
		case http.MethodGet:
			getProjectHandler(w, r)
		case http.MethodPut:
			updateProjectHandler(w, r)
		case http.MethodDelete:
			deleteProjectHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})
	mux.HandleFunc("/upload", uploadHandler)
	mux.HandleFunc("/progress", progressHandler)
	mux.HandleFunc("/images", getImagesHandler)

	logger.Info("Server starting", "port", 8080)
	if err := http.ListenAndServe(":8080", loggingMiddleware(corsMiddleware(mux))); err != nil {
		logger.Error("Server failed", "error", err)
		os.Exit(1)
	}
}
