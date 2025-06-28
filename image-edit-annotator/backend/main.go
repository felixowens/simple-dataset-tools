package main

import (
	"archive/zip"
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
	_ "golang.org/x/image/webp"
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
			logger.Error("Invalid image format",
				"error", err,
				"project_id", projectID,
				"filename", fileHeader.Filename,
			)
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
	var tasksCreated int
	for _, img := range images {
		// Check if task already exists for this image
		exists, err := taskExistsForImageA(projectID, img.ID)
		if err != nil {
			logger.Warn("Error checking if task exists",
				"error", err,
				"image_id", img.ID,
			)
			continue
		}
		if exists {
			logger.Debug("Task already exists for image, skipping",
				"image_id", img.ID,
				"project_id", projectID,
			)
			continue
		}

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

		tasksCreated++
		totalCandidates += len(candidateIDs)
	}

	var averageCandidates float64
	if tasksCreated > 0 {
		averageCandidates = float64(totalCandidates) / float64(tasksCreated)
	}
	return &TaskGenerationResponse{
		TasksCreated:      tasksCreated,
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

func getTasksHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projectID := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/projects/"), "/tasks")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Check if project exists
	project, err := getProject(projectID)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for tasks", err, slog.String("project_id", projectID))
		return
	}
	if project == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	tasks, err := getTasksByProjectID(projectID)
	if err != nil {
		http.Error(w, "Failed to get tasks", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get tasks", err, slog.String("project_id", projectID))
		return
	}

	if tasks == nil {
		tasks = []Task{}
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(tasks)
}

func getTaskHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	taskID := r.URL.Path[len("/tasks/"):]
	if taskID == "" {
		http.Error(w, "Task ID is required", http.StatusBadRequest)
		return
	}

	task, err := getTask(taskID)
	if err != nil {
		http.Error(w, "Failed to get task", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get task", err, slog.String("task_id", taskID))
		return
	}

	if task == nil {
		http.Error(w, "Task not found", http.StatusNotFound)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(task)
}

func updateTaskHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "PUT" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	taskID := r.URL.Path[len("/tasks/"):]
	if taskID == "" {
		http.Error(w, "Task ID is required", http.StatusBadRequest)
		return
	}

	// Check if task exists
	existingTask, err := getTask(taskID)
	if err != nil {
		http.Error(w, "Failed to get task", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get task for update", err, slog.String("task_id", taskID))
		return
	}
	if existingTask == nil {
		http.Error(w, "Task not found", http.StatusNotFound)
		return
	}

	var updatedTask Task
	if err := json.NewDecoder(r.Body).Decode(&updatedTask); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	updatedTask.ID = taskID // Ensure the ID from the URL is used

	if err := updateTask(&updatedTask); err != nil {
		http.Error(w, "Failed to update task", http.StatusInternalServerError)
		logError(r.Context(), "Failed to update task", err, slog.String("task_id", taskID))
		return
	}

	// Return the updated task
	task, err := getTask(taskID)
	if err != nil {
		http.Error(w, "Failed to get updated task", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get updated task", err, slog.String("task_id", taskID))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(task)
}

func serveImageHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract project ID and image path from URL
	// URL format: /projects/{projectId}/images/{imagePath}
	pathParts := strings.Split(strings.TrimPrefix(r.URL.Path, "/projects/"), "/")
	if len(pathParts) < 3 || pathParts[1] != "images" {
		http.Error(w, "Invalid image path", http.StatusBadRequest)
		return
	}

	projectID := pathParts[0]
	imagePath := strings.Join(pathParts[2:], "/")

	// Construct file path
	filePath := filepath.Join("data", "projects", projectID, "images", imagePath)

	// Security check: ensure the path is within the project directory
	absProjectDir, err := filepath.Abs(filepath.Join("data", "projects", projectID))
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	absFilePath, err := filepath.Abs(filePath)
	if err != nil {
		http.Error(w, "Internal server error", http.StatusInternalServerError)
		return
	}

	if !strings.HasPrefix(absFilePath, absProjectDir) {
		http.Error(w, "Access denied", http.StatusForbidden)
		return
	}

	// Check if file exists
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		http.Error(w, "Image not found", http.StatusNotFound)
		return
	}

	// Serve the file
	http.ServeFile(w, r, filePath)
}

func exportJSONLHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projectID := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/projects/"), "/export/jsonl")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Check if project exists
	project, err := getProject(projectID)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for JSONL export", err, slog.String("project_id", projectID))
		return
	}
	if project == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	// Get completed tasks
	tasks, err := getTasksByProjectID(projectID)
	if err != nil {
		http.Error(w, "Failed to get tasks", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get tasks for JSONL export", err, slog.String("project_id", projectID))
		return
	}

	// Get all images for path lookup
	images, err := getImagesByProjectID(projectID)
	if err != nil {
		http.Error(w, "Failed to get images", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get images for JSONL export", err, slog.String("project_id", projectID))
		return
	}

	// Create image lookup map
	imageMap := make(map[string]*Image)
	for i := range images {
		imageMap[images[i].ID] = &images[i]
	}

	// Set response headers for file download
	w.Header().Set("Content-Type", "application/x-ndjson")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s_annotations.jsonl\"", project.Name))

	// Write JSONL format
	for _, task := range tasks {
		// Only export completed tasks (not skipped, has imageB or prompt)
		if task.Skipped || (!task.ImageBId.Valid && !task.Prompt.Valid) {
			continue
		}

		imageA := imageMap[task.ImageAID]
		if imageA == nil {
			continue
		}

		// Create export record
		record := map[string]interface{}{
			"a": imageA.Path,
		}

		if task.ImageBId.Valid {
			imageB := imageMap[task.ImageBId.String]
			if imageB != nil {
				record["b"] = imageB.Path
			}
		}

		if task.Prompt.Valid {
			record["prompt"] = task.Prompt.String
		}

		// Write JSON line
		jsonData, err := json.Marshal(record)
		if err != nil {
			logError(r.Context(), "Failed to marshal task record", err, slog.String("task_id", task.ID))
			continue
		}

		w.Write(jsonData)
		w.Write([]byte("\n"))
	}

	logInfo(r.Context(), "JSONL export completed", slog.String("project_id", projectID))
}

func exportAIToolkitHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	projectID := strings.TrimSuffix(strings.TrimPrefix(r.URL.Path, "/projects/"), "/export/ai-toolkit")
	if projectID == "" {
		http.Error(w, "Project ID is required", http.StatusBadRequest)
		return
	}

	// Check if project exists
	project, err := getProject(projectID)
	if err != nil {
		http.Error(w, "Failed to get project", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get project for AI-toolkit export", err, slog.String("project_id", projectID))
		return
	}
	if project == nil {
		http.Error(w, "Project not found", http.StatusNotFound)
		return
	}

	// Get completed tasks
	tasks, err := getTasksByProjectID(projectID)
	if err != nil {
		http.Error(w, "Failed to get tasks", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get tasks for AI-toolkit export", err, slog.String("project_id", projectID))
		return
	}

	// Get all images for path lookup
	images, err := getImagesByProjectID(projectID)
	if err != nil {
		http.Error(w, "Failed to get images", http.StatusInternalServerError)
		logError(r.Context(), "Failed to get images for AI-toolkit export", err, slog.String("project_id", projectID))
		return
	}

	// Create image lookup map
	imageMap := make(map[string]*Image)
	for i := range images {
		imageMap[images[i].ID] = &images[i]
	}

	// Create temporary export directory
	exportDir := filepath.Join("data", "exports", projectID+"-ai-toolkit")
	sourceDir := filepath.Join(exportDir, "source")
	targetDir := filepath.Join(exportDir, "target")

	// Clean and create directories
	os.RemoveAll(exportDir)
	if err := os.MkdirAll(sourceDir, 0755); err != nil {
		http.Error(w, "Failed to create export directories", http.StatusInternalServerError)
		logError(r.Context(), "Failed to create source directory", err)
		return
	}
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		http.Error(w, "Failed to create export directories", http.StatusInternalServerError)
		logError(r.Context(), "Failed to create target directory", err)
		return
	}

	// Process completed tasks
	exportCount := 0
	for _, task := range tasks {
		// Only export completed tasks with both imageB and prompt
		if task.Skipped || !task.ImageBId.Valid || !task.Prompt.Valid {
			continue
		}

		imageA := imageMap[task.ImageAID]
		imageB := imageMap[task.ImageBId.String]
		if imageA == nil || imageB == nil {
			continue
		}

		// Generate unique filename for this pair
		baseName := fmt.Sprintf("pair_%04d", exportCount+1)

		// Copy source image
		sourceImagePath := filepath.Join("data", "projects", projectID, imageA.Path)
		destSourcePath := filepath.Join(sourceDir, baseName+filepath.Ext(imageA.Path))
		if err := copyFile(sourceImagePath, destSourcePath); err != nil {
			logError(r.Context(), "Failed to copy source image", err,
				slog.String("source", sourceImagePath),
				slog.String("dest", destSourcePath))
			continue
		}

		// Copy target image
		targetImagePath := filepath.Join("data", "projects", projectID, imageB.Path)
		destTargetPath := filepath.Join(targetDir, baseName+filepath.Ext(imageB.Path))
		if err := copyFile(targetImagePath, destTargetPath); err != nil {
			logError(r.Context(), "Failed to copy target image", err,
				slog.String("source", targetImagePath),
				slog.String("dest", destTargetPath))
			continue
		}

		// Write caption files in both source and target folders
		sourceCaptionPath := filepath.Join(sourceDir, baseName+".txt")
		targetCaptionPath := filepath.Join(targetDir, baseName+".txt")

		captionContent := []byte(task.Prompt.String)

		if err := os.WriteFile(sourceCaptionPath, captionContent, 0644); err != nil {
			logError(r.Context(), "Failed to write source caption file", err, slog.String("path", sourceCaptionPath))
			continue
		}

		if err := os.WriteFile(targetCaptionPath, captionContent, 0644); err != nil {
			logError(r.Context(), "Failed to write target caption file", err, slog.String("path", targetCaptionPath))
			continue
		}

		exportCount++
	}

	// Create ZIP archive
	zipPath := filepath.Join("data", "exports", project.Name+"_ai-toolkit.zip")
	if err := createZipArchive(exportDir, zipPath); err != nil {
		http.Error(w, "Failed to create ZIP archive", http.StatusInternalServerError)
		logError(r.Context(), "Failed to create ZIP archive", err)
		return
	}

	// Serve the ZIP file
	w.Header().Set("Content-Type", "application/zip")
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=\"%s_ai-toolkit.zip\"", project.Name))

	http.ServeFile(w, r, zipPath)

	// Clean up temporary files
	go func() {
		os.RemoveAll(exportDir)
		os.Remove(zipPath)
	}()

	logInfo(r.Context(), "AI-toolkit export completed",
		slog.String("project_id", projectID),
		slog.Int("exported_pairs", exportCount))
}

// Helper function to copy files
func copyFile(src, dst string) error {
	source, err := os.Open(src)
	if err != nil {
		return err
	}
	defer source.Close()

	destination, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer destination.Close()

	_, err = io.Copy(destination, source)
	return err
}

// Helper function to create ZIP archive
func createZipArchive(sourceDir, zipPath string) error {
	zipFile, err := os.Create(zipPath)
	if err != nil {
		return err
	}
	defer zipFile.Close()

	zipWriter := zip.NewWriter(zipFile)
	defer zipWriter.Close()

	return filepath.Walk(sourceDir, func(filePath string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			return nil
		}

		relPath, err := filepath.Rel(sourceDir, filePath)
		if err != nil {
			return err
		}

		zipFileWriter, err := zipWriter.Create(relPath)
		if err != nil {
			return err
		}

		file, err := os.Open(filePath)
		if err != nil {
			return err
		}
		defer file.Close()

		_, err = io.Copy(zipFileWriter, file)
		return err
	})
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
		if strings.HasSuffix(r.URL.Path, "/tasks") && r.Method == http.MethodGet {
			getTasksHandler(w, r)
			return
		}
		if strings.Contains(r.URL.Path, "/images/") && r.Method == http.MethodGet {
			serveImageHandler(w, r)
			return
		}
		if strings.HasSuffix(r.URL.Path, "/export/jsonl") && r.Method == http.MethodGet {
			exportJSONLHandler(w, r)
			return
		}
		if strings.HasSuffix(r.URL.Path, "/export/ai-toolkit") && r.Method == http.MethodGet {
			exportAIToolkitHandler(w, r)
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
	mux.HandleFunc("/tasks/", func(w http.ResponseWriter, r *http.Request) {
		switch r.Method {
		case http.MethodGet:
			getTaskHandler(w, r)
		case http.MethodPut:
			updateTaskHandler(w, r)
		default:
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		}
	})

	logger.Info("Server starting", "port", 8080)
	if err := http.ListenAndServe(":8080", loggingMiddleware(corsMiddleware(mux))); err != nil {
		logger.Error("Server failed", "error", err)
		os.Exit(1)
	}
}
