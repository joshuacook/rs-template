import React, { createContext, useContext, ReactNode } from 'react';
import Constants from 'expo-constants';
import { useAuth } from './AuthContext';

// Get the API URL dynamically
const getApiUrl = () => {
  // First check for explicit environment variable
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  
  // Check for extra config from app.json
  if (Constants.expoConfig?.extra?.apiUrl) {
    return Constants.expoConfig.extra.apiUrl;
  }
  
  // In development, try to use the debugger host
  if (__DEV__ && Constants.manifest?.debuggerHost) {
    const debuggerHost = Constants.manifest.debuggerHost;
    const hostWithoutPort = debuggerHost.split(':')[0];
    return `http://${hostWithoutPort}:8080`;
  }
  
  // Fallback to localhost (will work on Android emulator)
  return 'http://localhost:8080';
};

const API_URL = getApiUrl();

interface ApiContextType {
  apiUrl: string;
  get: (endpoint: string) => Promise<any>;
  post: (endpoint: string, data: any) => Promise<any>;
  put: (endpoint: string, data: any) => Promise<any>;
  delete: (endpoint: string) => Promise<any>;
  uploadFile: (file: any) => Promise<any>;
}

const ApiContext = createContext<ApiContextType | undefined>(undefined);

export function ApiProvider({ children }: { children: ReactNode }) {
  const { token } = useAuth();

  const getHeaders = () => {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return headers;
  };

  const handleResponse = async (response: Response) => {
    if (!response.ok) {
      const error = await response.text();
      throw new Error(error || `HTTP error! status: ${response.status}`);
    }
    
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return response.json();
    }
    
    return response.text();
  };

  const get = async (endpoint: string) => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'GET',
      headers: getHeaders(),
    });
    return handleResponse(response);
  };

  const post = async (endpoint: string, data: any) => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  };

  const put = async (endpoint: string, data: any) => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'PUT',
      headers: getHeaders(),
      body: JSON.stringify(data),
    });
    return handleResponse(response);
  };

  const deleteRequest = async (endpoint: string) => {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    return handleResponse(response);
  };

  const uploadFile = async (file: any) => {
    const formData = new FormData();
    formData.append('file', file as any);

    const response = await fetch(`${API_URL}/files/upload`, {
      method: 'POST',
      headers: {
        'Authorization': token ? `Bearer ${token}` : '',
      },
      body: formData,
    });
    
    return handleResponse(response);
  };

  return (
    <ApiContext.Provider
      value={{
        apiUrl: API_URL,
        get,
        post,
        put,
        delete: deleteRequest,
        uploadFile,
      }}
    >
      {children}
    </ApiContext.Provider>
  );
}

export function useApi() {
  const context = useContext(ApiContext);
  if (context === undefined) {
    throw new Error('useApi must be used within an ApiProvider');
  }
  return context;
}