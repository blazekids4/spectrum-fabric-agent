import { type NextRequest, NextResponse } from "next/server"

// Backend URL configuration - now points to the main app.py endpoint
const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001"
const CHAT_ENDPOINT = `${BACKEND_BASE_URL}/chat`

// Timeout configuration for long-running requests
const REQUEST_TIMEOUT = 120000 // 2 minutes for complex analyses

// Session management
interface SessionCache {
  [key: string]: {
    sessionId: string
    lastActivity: number
  }
}

// In-memory session cache (in production, use Redis or similar)
const sessionCache: SessionCache = {}

// Helper function to get or create session
async function getOrCreateSession(clientId?: string): Promise<string> {
  // Check if we have a cached session
  if (clientId && sessionCache[clientId]) {
    const session = sessionCache[clientId]
    const sessionAge = Date.now() - session.lastActivity
    
    // Return cached session if it's less than 30 minutes old
    if (sessionAge < 30 * 60 * 1000) {
      session.lastActivity = Date.now()
      return session.sessionId
    }
  }

  // Create new session
  try {
    const response = await fetch(`${BACKEND_BASE_URL}/session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })

    if (response.ok) {
      const data = await response.json()
      const sessionId = data.session_id
      
      // Cache the session if we have a client ID
      if (clientId) {
        sessionCache[clientId] = {
          sessionId,
          lastActivity: Date.now()
        }
      }
      
      return sessionId
    }
  } catch (error) {
    console.error("Failed to create session:", error)
  }

  // Fallback to undefined (backend will create one)
  return undefined as any
}

export async function POST(request: NextRequest) {
  // Set up abort controller for timeout
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT)

  try {
    const body = await request.json()
    
    // Extract client identifier from request headers or body
    const clientId = request.headers.get("x-client-id") || 
                    body.clientId || 
                    request.headers.get("x-forwarded-for") || 
                    "default"

    // Get or create session
    const sessionId = body.session_id || await getOrCreateSession(clientId)

    // Prepare the request payload
    const chatRequest = {
      session_id: sessionId,
      message: body.message || body.query, // Support both 'message' and 'query' fields
      context: {
        clientId,
        timestamp: new Date().toISOString(),
        source: "web-frontend",
        ...body.context // Merge any additional context
      }
    }

    // Log the request for monitoring
    console.log(`[Chat API] Request from ${clientId}:`, {
      sessionId: chatRequest.session_id,
      messageLength: chatRequest.message?.length,
      hasContext: !!chatRequest.context
    })

    // Forward to the backend chat endpoint
    const response = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: { 
        "Content-Type": "application/json",
        "X-Client-Id": clientId,
        "X-Request-Id": crypto.randomUUID() // For request tracing
      },
      body: JSON.stringify(chatRequest),
      signal: controller.signal
    })

    // Clear the timeout
    clearTimeout(timeoutId)

    // Handle non-OK responses
    if (!response.ok) {
      const errorText = await response.text()
      console.error(`[Chat API] Backend error (${response.status}):`, errorText)
      
      // Try to parse as JSON for structured error
      let errorDetail = errorText
      try {
        const errorJson = JSON.parse(errorText)
        errorDetail = errorJson.error || errorJson.detail || errorText
      } catch {
        // Keep original text if not JSON
      }

      return NextResponse.json(
        { 
          error: "Backend service error", 
          detail: errorDetail,
          status: response.status
        }, 
        { status: response.status }
      )
    }

    // Parse successful response
    const data = await response.json()

    // Update session cache if needed
    if (data.session_id && clientId) {
      sessionCache[clientId] = {
        sessionId: data.session_id,
        lastActivity: Date.now()
      }
    }

    // Log successful response
    console.log(`[Chat API] Response for ${clientId}:`, {
      sessionId: data.session_id,
      replyLength: data.reply?.length,
      hasSources: !!data.sources?.length,
      hasMetadata: !!data.metadata
    })

    // Return the response with additional headers
    return NextResponse.json(data, {
      headers: {
        "X-Session-Id": data.session_id || "",
        "X-Request-Id": response.headers.get("X-Request-Id") || "",
        "Cache-Control": "no-store" // Prevent caching of chat responses
      }
    })

  } catch (error: any) {
    // Clear timeout on error
    clearTimeout(timeoutId)

    console.error("[Chat API] Error:", error)

    // Handle specific error types
    if (error.name === "AbortError") {
      return NextResponse.json(
        { error: "Request timeout", detail: "The request took too long to process" },
        { status: 504 }
      )
    }

    if (error.code === "ECONNREFUSED") {
      return NextResponse.json(
        { error: "Backend unavailable", detail: "Cannot connect to backend service" },
        { status: 503 }
      )
    }

    // Generic error response
    return NextResponse.json(
      { 
        error: "Internal server error", 
        detail: error.message || "An unexpected error occurred"
      },
      { status: 500 }
    )
  }
}

// Health check endpoint
export async function GET(request: NextRequest) {
  try {
    // Check backend health
    const response = await fetch(BACKEND_BASE_URL, {
      method: "GET",
      signal: AbortSignal.timeout(5000) // 5 second timeout for health check
    })

    if (response.ok) {
      const data = await response.json()
      return NextResponse.json({
        status: "healthy",
        backend: data,
        frontend: {
          version: process.env.npm_package_version || "unknown",
          environment: process.env.NODE_ENV,
          activeSessions: Object.keys(sessionCache).length
        }
      })
    }

    return NextResponse.json(
      { status: "unhealthy", error: "Backend not responding" },
      { status: 503 }
    )
  } catch (error) {
    return NextResponse.json(
      { status: "unhealthy", error: "Cannot reach backend" },
      { status: 503 }
    )
  }
}

// Session management endpoints
export async function DELETE(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const sessionId = searchParams.get("session_id")
    const clientId = request.headers.get("x-client-id") || "default"

    if (sessionId) {
      // Remove from cache
      if (sessionCache[clientId]?.sessionId === sessionId) {
        delete sessionCache[clientId]
      }

      // Note: You might want to call a backend endpoint to clean up the session
      // await fetch(`${BACKEND_BASE_URL}/session/${sessionId}`, { method: "DELETE" })

      return NextResponse.json({ message: "Session cleared" })
    }

    return NextResponse.json(
      { error: "Session ID required" },
      { status: 400 }
    )
  } catch (error) {
    console.error("[Chat API] Error clearing session:", error)
    return NextResponse.json(
      { error: "Failed to clear session" },
      { status: 500 }
    )
  }
}

// Clean up old sessions periodically (every 5 minutes)
if (typeof global !== "undefined" && !(global as any).__sessionCleanupInterval) {
  (global as any).__sessionCleanupInterval = setInterval(() => {
    const now = Date.now()
    const maxAge = 30 * 60 * 1000 // 30 minutes
    
    for (const [clientId, session] of Object.entries(sessionCache)) {
      if (now - session.lastActivity > maxAge) {
        delete sessionCache[clientId]
      }
    }
    
    console.log(`[Chat API] Session cleanup: ${Object.keys(sessionCache).length} active sessions`)
  }, 5 * 60 * 1000)
}