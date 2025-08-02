package main

import (
	"context"
	"encoding/json"
	"fmt"
	"path/filepath"
	"sync"
	"time"
)

// AutoCaptionManager handles bulk auto captioning with rate limiting
type AutoCaptionManager struct {
	mutex               sync.RWMutex
	activeProjects      map[string]*AutoCaptionSession
	progressClients     map[string]chan AutoCaptionProgress
	progressClientsMu   sync.RWMutex
}

// AutoCaptionSession represents an active auto captioning session
type AutoCaptionSession struct {
	ProjectID       string
	Config          AutoCaptionConfig
	Progress        AutoCaptionProgress
	CancelFunc      context.CancelFunc
	Tasks           []CaptionTask
	CurrentIndex    int
	mutex           sync.RWMutex
}

var autoCaptionManager *AutoCaptionManager

func init() {
	autoCaptionManager = &AutoCaptionManager{
		activeProjects:  make(map[string]*AutoCaptionSession),
		progressClients: make(map[string]chan AutoCaptionProgress),
	}
}

// StartAutoCaptioning begins the auto captioning process for a project
func (acm *AutoCaptionManager) StartAutoCaptioning(projectID string, config AutoCaptionConfig) error {
	acm.mutex.Lock()
	defer acm.mutex.Unlock()

	// Check if already running
	if _, exists := acm.activeProjects[projectID]; exists {
		return fmt.Errorf("auto captioning already running for project %s", projectID)
	}

	// Get project to validate and check API configuration
	project, err := getProject(projectID)
	if err != nil {
		return fmt.Errorf("failed to get project: %v", err)
	}
	if project == nil {
		return fmt.Errorf("project not found")
	}

	// Check if caption API is configured
	if project.CaptionAPI == nil {
		return fmt.Errorf("caption API not configured for this project")
	}

	// Get pending caption tasks
	allTasks, err := getCaptionTasksByProjectID(projectID)
	if err != nil {
		return fmt.Errorf("failed to get caption tasks: %v", err)
	}

	// Filter to pending tasks only
	var pendingTasks []CaptionTask
	for _, task := range allTasks {
		if task.Status == "pending" && !task.Skipped {
			pendingTasks = append(pendingTasks, task)
		}
	}

	if len(pendingTasks) == 0 {
		return fmt.Errorf("no pending tasks found for auto captioning")
	}

	// Create session context
	ctx, cancel := context.WithCancel(context.Background())

	// Initialize session
	session := &AutoCaptionSession{
		ProjectID:  projectID,
		Config:     config,
		CancelFunc: cancel,
		Tasks:      pendingTasks,
		Progress: AutoCaptionProgress{
			ProjectID: projectID,
			Status:    "running",
			Total:     len(pendingTasks),
			StartedAt: time.Now().Format(time.RFC3339),
		},
	}

	acm.activeProjects[projectID] = session

	// Start processing in background
	go acm.processAutoCaptioning(ctx, session, project)

	return nil
}

// CancelAutoCaptioning stops the auto captioning process for a project
func (acm *AutoCaptionManager) CancelAutoCaptioning(projectID string) error {
	acm.mutex.Lock()
	defer acm.mutex.Unlock()

	session, exists := acm.activeProjects[projectID]
	if !exists {
		return fmt.Errorf("no active auto captioning session for project %s", projectID)
	}

	session.CancelFunc()
	session.mutex.Lock()
	session.Progress.Status = "cancelled"
	session.Progress.CompletedAt = time.Now().Format(time.RFC3339)
	session.mutex.Unlock()

	// Send final progress update
	acm.sendProgressUpdate(projectID, session.Progress)

	delete(acm.activeProjects, projectID)
	return nil
}

// GetAutoCaptionStatus returns the current status of auto captioning for a project
func (acm *AutoCaptionManager) GetAutoCaptionStatus(projectID string) (*AutoCaptionStatusResponse, error) {
	acm.mutex.RLock()
	defer acm.mutex.RUnlock()

	session, exists := acm.activeProjects[projectID]
	if !exists {
		return &AutoCaptionStatusResponse{
			IsActive: false,
		}, nil
	}

	session.mutex.RLock()
	progress := session.Progress
	session.mutex.RUnlock()

	return &AutoCaptionStatusResponse{
		Progress: &progress,
		IsActive: true,
	}, nil
}

// processAutoCaptioning handles the actual captioning process
func (acm *AutoCaptionManager) processAutoCaptioning(ctx context.Context, session *AutoCaptionSession, project *Project) {
	defer func() {
		acm.mutex.Lock()
		delete(acm.activeProjects, session.ProjectID)
		acm.mutex.Unlock()
	}()

	// Parse caption API config
	var apiConfig CaptionAPIConfig
	if err := json.Unmarshal([]byte(*project.CaptionAPI), &apiConfig); err != nil {
		acm.updateProgress(session, "error", fmt.Sprintf("Invalid caption API configuration: %v", err))
		return
	}

	// Create captioning service
	captioningService, err := CreateCaptioningService(&apiConfig)
	if err != nil {
		acm.updateProgress(session, "error", fmt.Sprintf("Failed to create captioning service: %v", err))
		return
	}

	// Calculate delay between requests based on RPM
	requestDelay := time.Duration(60000/session.Config.RPM) * time.Millisecond

	// Get system prompt
	systemPrompt := "Describe this image in detail for training a diffusion model. Focus on the visual elements, composition, style, and any notable features."
	if project.SystemPrompt != nil && *project.SystemPrompt != "" {
		systemPrompt = *project.SystemPrompt
	}

	// Process each task
	for i, task := range session.Tasks {
		select {
		case <-ctx.Done():
			return
		default:
		}

		session.mutex.Lock()
		session.CurrentIndex = i
		session.Progress.CurrentTask = task.ID
		session.Progress.Processed = i
		session.mutex.Unlock()

		acm.sendProgressUpdate(session.ProjectID, session.Progress)

		// Process task with retries
		success := acm.processTaskWithRetries(ctx, task, session, captioningService, systemPrompt, project.ID)
		
		session.mutex.Lock()
		if success {
			session.Progress.Successful++
		} else {
			session.Progress.Failed++
		}
		session.mutex.Unlock()

		// Apply rate limiting delay (except for last task)
		if i < len(session.Tasks)-1 {
			select {
			case <-ctx.Done():
				return
			case <-time.After(requestDelay):
			}
		}
	}

	// Mark as completed
	session.mutex.Lock()
	session.Progress.Status = "completed"
	session.Progress.Processed = len(session.Tasks)
	session.Progress.CurrentTask = ""
	session.Progress.CompletedAt = time.Now().Format(time.RFC3339)
	finalProgress := session.Progress
	session.mutex.Unlock()

	acm.sendProgressUpdate(session.ProjectID, finalProgress)
}

// processTaskWithRetries handles a single task with retry logic
func (acm *AutoCaptionManager) processTaskWithRetries(ctx context.Context, task CaptionTask, session *AutoCaptionSession, service CaptioningService, systemPrompt, projectID string) bool {
	maxRetries := session.Config.MaxRetries
	if maxRetries <= 0 {
		maxRetries = 3
	}

	baseDelay := time.Duration(session.Config.RetryDelayMs) * time.Millisecond
	if baseDelay <= 0 {
		baseDelay = 1000 * time.Millisecond
	}

	for attempt := 0; attempt <= maxRetries; attempt++ {
		select {
		case <-ctx.Done():
			return false
		default:
		}

		// Get image
		image, err := getImage(task.ImageID)
		if err != nil {
			logger.Error("Failed to get image for auto captioning", "error", err, "task_id", task.ID)
			if attempt == maxRetries {
				return false
			}
			time.Sleep(baseDelay * time.Duration(attempt+1))
			continue
		}

		if image == nil {
			logger.Error("Image not found for auto captioning", "task_id", task.ID, "image_id", task.ImageID)
			return false
		}

		// Convert image to base64
		imagePath := filepath.Join("data", "projects", projectID, image.Path)
		imageBase64, err := ImageToBase64(imagePath)
		if err != nil {
			logger.Error("Failed to encode image for auto captioning", "error", err, "path", imagePath)
			if attempt == maxRetries {
				return false
			}
			time.Sleep(baseDelay * time.Duration(attempt+1))
			continue
		}

		// Generate caption
		caption, err := service.GenerateCaption(imageBase64, systemPrompt)
		if err != nil {
			logger.Error("Failed to generate caption", "error", err, "task_id", task.ID, "attempt", attempt+1)
			if attempt == maxRetries {
				return false
			}
			time.Sleep(baseDelay * time.Duration(attempt+1))
			continue
		}

		// Update task in database
		task.Caption.String = caption
		task.Caption.Valid = true
		task.Status = "auto_generated"

		if err := updateCaptionTask(&task); err != nil {
			logger.Error("Failed to update caption task", "error", err, "task_id", task.ID)
			if attempt == maxRetries {
				return false
			}
			time.Sleep(baseDelay * time.Duration(attempt+1))
			continue
		}

		logger.Info("Successfully generated auto caption", "task_id", task.ID, "caption_length", len(caption))
		return true
	}

	return false
}

// updateProgress updates the session progress with error handling
func (acm *AutoCaptionManager) updateProgress(session *AutoCaptionSession, status, errorMessage string) {
	session.mutex.Lock()
	session.Progress.Status = status
	session.Progress.ErrorMessage = errorMessage
	if status == "error" || status == "completed" || status == "cancelled" {
		session.Progress.CompletedAt = time.Now().Format(time.RFC3339)
	}
	progress := session.Progress
	session.mutex.Unlock()

	acm.sendProgressUpdate(session.ProjectID, progress)
}

// sendProgressUpdate sends progress updates to connected clients
func (acm *AutoCaptionManager) sendProgressUpdate(projectID string, progress AutoCaptionProgress) {
	acm.progressClientsMu.RLock()
	client, exists := acm.progressClients[projectID]
	acm.progressClientsMu.RUnlock()

	if exists {
		select {
		case client <- progress:
		default:
			// Client channel is full, skip this update
		}
	}
}

// AddProgressClient adds a progress update client for a project
func (acm *AutoCaptionManager) AddProgressClient(projectID string, client chan AutoCaptionProgress) {
	acm.progressClientsMu.Lock()
	acm.progressClients[projectID] = client
	acm.progressClientsMu.Unlock()
}

// RemoveProgressClient removes a progress update client for a project
func (acm *AutoCaptionManager) RemoveProgressClient(projectID string) {
	acm.progressClientsMu.Lock()
	if client, exists := acm.progressClients[projectID]; exists {
		close(client)
		delete(acm.progressClients, projectID)
	}
	acm.progressClientsMu.Unlock()
}