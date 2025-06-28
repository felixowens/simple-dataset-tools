import axios from 'axios';

const API_BASE_URL = 'http://localhost:8080';

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
});

export const ping = () => api.get('/ping');

export interface Project {
  id: string;
  name: string;
  version: string;
}

export const createProject = (project: Omit<Project, 'id'>) => api.post<Project>('/projects', project);
export const getProject = (id: string) => api.get<Project>(`/projects/${id}`);
export const listProjects = () => api.get<Project[]>('/projects');
export const updateProject = (id: string, project: Omit<Project, 'id'>) => api.put<Project>(`/projects/${id}`, project);
export const deleteProject = (id: string) => api.delete(`/projects/${id}`);

export interface Image {
  id: string;
  projectId: string;
  path: string;
  pHash: string;
}

export interface ProgressUpdate {
  projectId: string;
  filename: string;
  progress: number;
  total: number;
  status: string;
  errorMessage?: string;
}

export const uploadFiles = (projectId: string, files: FileList) => {
  const formData = new FormData();
  Array.from(files).forEach(file => {
    formData.append('files', file);
  });
  
  return api.post(`/upload?projectId=${projectId}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

export const getImages = (projectId: string) => api.get<Image[]>(`/images?projectId=${projectId}`);

export const createProgressEventSource = (projectId: string) => {
  return new EventSource(`${API_BASE_URL}/progress?projectId=${projectId}`);
};