/**
 * API Types for Charter VIP Frontend
 */

// Chat API Types
export interface ChatRequest {
  session_id?: string
  message: string
  context?: ChatContext
  clientId?: string
}

export interface ChatContext {
  clientId?: string
  timestamp?: string
  source?: string
  [key: string]: any // Allow additional context fields
}

export interface ChatResponse {
  session_id: string
  reply: string | null
  metadata?: ChatMetadata
  sources?: string[]
}

export interface ChatMetadata {
  message_count?: number
  analysis_type?: string
  agents_used?: string[]
  insights?: Record<string, any>
  [key: string]: any
}


// Session Types
export interface SessionInfo {
  session_id: string
  info: {
    history: ChatMessage[]
    created_at: string
    metadata: Record<string, any>
  }
}

export interface ChatMessage {
  role: "user" | "assistant"
  text: string
  timestamp: string
  sources?: string[]
}

// Error Types
export interface APIError {
  error: string
  detail?: string
  status?: number
}

// Health Check Types
export interface HealthStatus {
  status: "healthy" | "unhealthy"
  backend?: {
    status: string
    service: string
    version: string
    capabilities: {
      fabric_data_agent: boolean
      multi_agent_analysis: boolean
    }
  }
  frontend?: {
    version: string
    environment: string
    activeSessions: number
  }
  error?: string
}

// Utility type guards
export function isAPIError(response: any): response is APIError {
  return response && typeof response.error === "string"
}

export function isChatResponse(response: any): response is ChatResponse {
  return response && typeof response.session_id === "string"
}