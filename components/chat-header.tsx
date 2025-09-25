import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { RefreshCw, Activity } from "lucide-react"
import { useState, useEffect } from "react"
import { cn } from "@/lib/utils"
import Image from "next/image"

interface ChatHeaderProps {
  onClearSession?: () => void
}

export function ChatHeader({ onClearSession }: ChatHeaderProps) {
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null)

  useEffect(() => {
    // Check backend health on mount
    const checkHealth = async () => {
      try {
        const response = await fetch('/api/health')
        if (response.ok) {
          const health = await response.json()
          setIsHealthy(health.status === "healthy")
        } else {
          setIsHealthy(false)
        }
      } catch (error) {
        console.error('Health check failed:', error)
        setIsHealthy(false)
      }
    }
    checkHealth()

    // Recheck every 30 seconds
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="rounded-none border-0 border-b p-4 bg-gradient-to-r from-primary/1 to-primary/2">
      <div className="flex items-center justify-between">
        {/* Left: Spectrum Logo */}
        <div className="flex-shrink-0">
          <Image
            src="/spec_large.png"
            alt="Spectrum VIP Assistant Logo"
            width={120}
            height={120}
            className="object-contain"
            priority
          />
        </div>
        
        {/* Center: Ask AI-Leen */}
        <div className="flex-1 flex justify-center">
          <div className="flex items-center gap-3">
            <img src="/AI_icon.jpg" alt="AI-Leen Icon" className="h-8 w-8 rounded-full" />
            <div>
              <h2 className="text-lg font-semibold">Ask AI-Leen</h2>
            </div>
          </div>
        </div>
        
        {/* Right: Status and New Chat button */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="flex items-center gap-1">
            <Activity className={cn("h-3 w-3", isHealthy ? "text-green-500" : "text-red-500")} />
            <span className="text-xs text-muted-foreground">
              {isHealthy === null ? "Checking..." : isHealthy ? "Connected" : "Disconnected"}
            </span>
          </div>
          
          {onClearSession && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearSession}
              className="h-8 px-2"
              title="Start new conversation"
            >
              <RefreshCw className="h-4 w-4" />
              <span className="ml-1 text-xs">New Chat</span>
            </Button>
          )}
        </div>
      </div>
    </Card>
  )
}