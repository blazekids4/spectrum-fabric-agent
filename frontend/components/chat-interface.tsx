"use client"

import { useState, useRef, useEffect } from "react"
import { ChatMessage } from "./chat-message"
import { ChatInput } from "./chat-input"
import { ChatHeader } from "./chat-header"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

interface Message {
  id: string
  content: string
  isUser: boolean
  timestamp: Date
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content:
        "Hello! I'm your Charter VIP Assistant. I'm here to help you with any questions about Charter's business intelligence. How can I assist you today?",
      isUser: false,
      timestamp: new Date(),
    },
  ])
  const [isLoading, setIsLoading] = useState(false)
  const scrollAreaRef = useRef<HTMLDivElement>(null)

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
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      isUser: true,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      // TODO: Replace with actual FastAPI backend call
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ message: content }),
      })

      if (!response.ok) {
        throw new Error("Failed to get response")
      }

      const data = await response.json()

      const assistantText =
        // Backend (FastAPI) returns { reply }
        data.reply ||
        // older/other shapes
        data.response || data.result || null

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content:
          assistantText ||
          "I'm sorry, I'm having trouble connecting to our systems right now. Please try again in a moment.",
        isUser: false,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMessage])
    } catch (error) {
      console.error("Chat error:", error)

      // Fallback response for demo purposes
      const fallbackMessage: Message = {
        id: (Date.now() + 1).toString(),
        content:
          "Thank you for your message. I'm currently connecting to our Azure AI systems to provide you with the best possible assistance. ",
        isUser: false,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, fallbackMessage])
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="flex flex-col  max-w-2xl mx-auto shadow-lg">
      <ChatHeader />

      <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message.content}
              isUser={message.isUser}
              timestamp={message.timestamp}
            />
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="flex items-center gap-2 p-3 bg-muted rounded-lg">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div className="w-2 h-2 bg-primary rounded-full animate-bounce"></div>
                </div>
                <span className="text-sm text-muted-foreground">Charter VIP is typing...</span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
    </Card>
  )
}
