/**
 * Chat Client for Charter VIP Frontend
 */
import type { ChatRequest, ChatResponse, APIError, HealthStatus } from "@/types/api"

export class ChatClient {
  private baseUrl: string
  private clientId: string

  constructor(clientId?: string) {
    this.baseUrl = "/api/chat"
    this.clientId = clientId || this.generateClientId()
  }

  private generateClientId(): string {
    // Generate a persistent client ID (store in localStorage in browser)
    if (typeof window !== "undefined") {
      let id = localStorage.getItem("charter-vip-client-id")
      if (!id) {
        id = `client-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        localStorage.setItem("charter-vip-client-id", id)
      }
      return id
    }
    return `server-${Date.now()}`
  }

  async sendMessage(
    message: string, 
    sessionId?: string | null,
    context?: Record<string, any>
  ): Promise<ChatResponse | APIError> {
    try {
      const response = await fetch(this.baseUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Client-Id": this.clientId
        },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          clientId: this.clientId,
          context
        } as ChatRequest)
      })

      const data = await response.json()
      
      if (!response.ok) {
        return data as APIError
      }

      // Store session ID for future use
      if (data.session_id && typeof window !== "undefined") {
        sessionStorage.setItem("charter-vip-session-id", data.session_id)
      }

      return data as ChatResponse
    } catch (error) {
      return {
        error: "Network error",
        detail: error instanceof Error ? error.message : "Failed to connect to server"
      }
    }
  }

  async checkHealth(): Promise<HealthStatus> {
    try {
      const response = await fetch(this.baseUrl, { method: "GET" })
      return await response.json()
    } catch (error) {
      return {
        status: "unhealthy",
        error: "Cannot reach chat service"
      }
    }
  }

  async clearSession(sessionId: string): Promise<void> {
    try {
      await fetch(`${this.baseUrl}?session_id=${sessionId}`, {
        method: "DELETE",
        headers: {
          "X-Client-Id": this.clientId
        }
      })
      
      // Clear from storage
      if (typeof window !== "undefined") {
        sessionStorage.removeItem("charter-vip-session-id")
      }
    } catch (error) {
      console.error("Failed to clear session:", error)
    }
  }

  getStoredSessionId(): string | null {
    if (typeof window !== "undefined") {
      return sessionStorage.getItem("charter-vip-session-id")
    }
    return null
  }
}

// Export singleton instance
export const chatClient = new ChatClient()