/**
 * API type definitions for Spectrum Fabric Agent
 */

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  context?: Record<string, any>
}

export interface ChatRequest {
  messages: ChatMessage[]
  session_id?: string | null
  clientId?: string
  context?: Record<string, any>
}

export interface ChatResponse {
  response: string
  session_id: string
  metadata?: {
    model?: string
    tokens?: number
    sources?: string[]
    analysisType?: string
    session_id?: string
    client_id?: string
    [key: string]: any
  }
}

export interface APIError {
  error: string
  detail?: string
  session_id?: string
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy'
  service?: string
  version?: string
  fabric_status?: string
  data_agent?: string
  timestamp?: string
  error?: string
  frontend?: string
  backend?: string
}

export interface ConfigResponse {
  environment: string
  version: string
  managed_identity_enabled: boolean
  data_agent_configured: boolean
  workspace_configured: boolean
  model: string
  features: {
    sessionManagement: boolean
    contextAware: boolean
    multiTurn: boolean
  }
}

export interface QueryRequest {
  question: string
  session_id?: string
  clientId?: string
}

export interface QueryResponse {
  response: string
  session_id: string
  metadata?: Record<string, any>
}

export interface Session {
  id: string
  client_id?: string
  created: string
  messages: ChatMessage[]
}

// Type guards
export function isChatResponse(data: any): data is ChatResponse {
  return data && typeof data.response === 'string' && typeof data.session_id === 'string'
}

export function isAPIError(data: any): data is APIError {
  return data && typeof data.error === 'string'
}

export function isHealthStatus(data: any): data is HealthStatus {
  return data && typeof data.status === 'string'
}