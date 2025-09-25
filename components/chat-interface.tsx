"use client"
import { SuggestedPrompts } from "./suggested-prompts"
import { useState, useRef, useEffect } from "react"
import { ChatMessage } from "./chat-message"
import { LoadingMessage } from "./loading-message"
import { ChatInput } from "./chat-input"
import { ChatHeader } from "./chat-header"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { AlertCircle } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
  metadata?: {
    sources?: string[]
    analysisType?: string
  }
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content:
        "Hello! I'm AI-Leen, your AI assistant for customer insights. How can I help you today?",
      isUser: false,
      timestamp: new Date(),
    },
  ])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

  // Initialize session on mount
  useEffect(() => {
    const storedSessionId = localStorage.getItem('chat-session-id')
    if (storedSessionId) {
      setSessionId(storedSessionId)
    }
  }, [])

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector("[data-radix-scroll-area-viewport]")
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight
      }
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (content: string) => {
    // Clear any previous errors
    setError(null)

    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      isUser: true,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // Call the Azure Functions API
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          messages: [
            {
              role: 'user',
              content: content
            }
          ],
          session_id: sessionId,
        }),
      })

      const result = await response.json()

      if (!response.ok || 'error' in result) {
        throw new Error(result.detail || result.error || 'Failed to send message')
      }

      // Update session ID if provided by the backend
      if (result.session_id && result.session_id !== sessionId) {
        setSessionId(result.session_id)
        localStorage.setItem('chat-session-id', result.session_id)
      }

      const assistantMessage: Message = {
        id: `ai-${Date.now()}`,
        content: result.response || "I couldn't generate a response. Please try again.",
        isUser: false,
        timestamp: new Date(),
        metadata: result.metadata
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Chat error:", error)
      setError(error instanceof Error ? error.message : "An unexpected error occurred")

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content:
          "I'm having trouble processing your request. Please ensure the backend is running and try again.",
        isUser: false,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearSession = async () => {
    if (sessionId) {
      try {
        // Call the Azure Functions API to delete the session
        await fetch(`/api/sessions/${sessionId}`, {
          method: 'DELETE',
        })
      } catch (error) {
        console.error("Failed to clear session on server:", error)
      }
      
      localStorage.removeItem('chat-session-id')
      setSessionId(null)
      setMessages([messages[0]]) // Keep only welcome message
      setError(null)
    }
  }

  return (
    <Card className="flex flex-col  max-w-4xl mx-auto shadow-lg">
      <ChatHeader onClearSession={handleClearSession} />

      {error && (
        <Alert variant="destructive" className="mx-4 mt-2">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message.content}
              isUser={message.isUser}
              timestamp={message.timestamp}
              metadata={message.metadata}
            />
          ))}

          {isLoading && <LoadingMessage />}
        </div>
      </ScrollArea>
      {messages.length === 1 && !isLoading && (
        <SuggestedPrompts onSelectPrompt={handleSendMessage} />
      )}
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </Card>
  )
}