"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Send, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface ChatInputProps {
  onSendMessage: (message: string) => void
  isLoading?: boolean
  disabled?: boolean
}

export function ChatInput({ onSendMessage, isLoading = false, disabled = false }: ChatInputProps) {
  const [message, setMessage] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim() && !isLoading && !disabled) {
      onSendMessage(message.trim())
      setMessage("")
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t bg-card">
      <Input
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask Charter VIP anything..."
        disabled={isLoading || disabled}
        className="flex-1 text-sm"
      />
      <Button
        type="submit"
        size="sm"
        disabled={!message.trim() || isLoading || disabled}
        className={cn("px-3 transition-all duration-200", "hover:scale-105 active:scale-95")}
      >
        {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
      </Button>
    </form>
  )
}
