import { useEffect, useState } from 'react'
import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card } from "@/components/ui/card"

const thinkingMessages = [
  "Analyzing customer data...",
  "Processing competitive intelligence...",
  "Searching for market insights...",
  "Correlating information sources...",
  "Analyzing industry trends...",
  "Examining customer behavior patterns...",
  "Comparing competitor strategies...",
  "Synthesizing insights from call transcripts...",
  "Identifying key market opportunities...",
  "Evaluating competitive positioning..."
]

interface LoadingMessageProps {
  className?: string
}

export function LoadingMessage({ className }: LoadingMessageProps) {
  const [messageIndex, setMessageIndex] = useState(0)
  
  // Rotate through messages every 2 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prevIndex) => (prevIndex + 1) % thinkingMessages.length)
    }, 2000)
    
    return () => clearInterval(interval)
  }, [])

  return (
    <div className={cn("flex gap-3 mb-4 justify-start", className)}>
      <Avatar className="h-8 w-8 mt-1">
        <AvatarImage src="/AI_icon_2.jpg" alt="Spectrum VIP" />
        <AvatarFallback className="bg-primary text-primary-foreground text-xs">CV</AvatarFallback>
      </Avatar>

      <div className="max-w-[80%] space-y-1 items-start">
        <Card className="p-3 text-sm leading-relaxed bg-card border relative overflow-hidden">
          <div className="text-pretty flex items-center">
            <span>{thinkingMessages[messageIndex]}</span>
            <span className="ml-1 animate-pulse">
              <Dots />
            </span>
          </div>
          
          {/* Animated gradient line at bottom */}
          <div className="absolute bottom-0 left-0 h-[2px] bg-gradient-to-r from-blue-500 via-purple-500 to-blue-500 w-full animate-shimmer" />
        </Card>

        <div className="flex items-center gap-2 px-1">
          <p className="text-xs text-muted-foreground text-left">
            {new Date().toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </div>
      </div>
    </div>
  )
}

// Animated dots component
function Dots() {
  return (
    <span className="inline-flex">
      <span className="animate-bounce [animation-delay:0.0s]">.</span>
      <span className="animate-bounce [animation-delay:0.2s]">.</span>
      <span className="animate-bounce [animation-delay:0.4s]">.</span>
    </span>
  );
}