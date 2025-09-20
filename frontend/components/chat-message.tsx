import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { FileText, Database, Globe } from "lucide-react"

interface ChatMessageProps {
  message: string
  isUser: boolean
  timestamp: Date
  metadata?: {
    sources?: string[]
    analysisType?: string
  }
}

export function ChatMessage({ message, isUser, timestamp, metadata }: ChatMessageProps) {
  const getSourceIcon = (source: string) => {
    if (source.toLowerCase().includes('fabric')) return <Database className="h-3 w-3" />
    if (source.toLowerCase().includes('web')) return <Globe className="h-3 w-3" />
    return <FileText className="h-3 w-3" />
  }

  return (
    <div className={cn("flex gap-3 mb-4", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <Avatar className="h-8 w-8 mt-1">
          <AvatarImage src="/AI_icon_2.jpg" alt="Spectrum VIP" />
          <AvatarFallback className="bg-primary text-primary-foreground text-xs">CV</AvatarFallback>
        </Avatar>
      )}

      <div className={cn("max-w-[80%] space-y-1", isUser ? "items-end" : "items-start")}>
        <Card
          className={cn(
            "p-3 text-sm leading-relaxed",
            isUser ? "bg-primary text-primary-foreground ml-auto" : "bg-card border",
          )}
        >
          <div className="text-pretty">
            {/**
             * Enhanced renderer for code blocks and formatting
             */}
            {message.split(/```(?:\w+)?\n?/).map((part, idx) => {
              const isCode = idx % 2 === 1
              if (isCode) {
                return (
                  <pre key={idx} className="bg-muted/50 p-2 rounded overflow-x-auto text-[13px] my-2">
                    <code>{part}</code>
                  </pre>
                )
              }

              // Non-code text: preserve newlines and format lists
              return (
                <div key={idx} className="whitespace-pre-wrap">
                  {part.split('\n').map((line, lineIdx) => {
                    // Format bullet points
                    if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
                      return (
                        <div key={lineIdx} className="ml-4 my-1">
                          {line}
                        </div>
                      )
                    }
                    // Format numbered lists
                    if (/^\d+\./.test(line.trim())) {
                      return (
                        <div key={lineIdx} className="ml-4 my-1">
                          {line}
                        </div>
                      )
                    }
                    return <div key={lineIdx}>{line}</div>
                  })}
                </div>
              )
            })}
          </div>
        </Card>

        <div className="flex items-center gap-2 px-1">
          <p className={cn("text-xs text-muted-foreground", isUser ? "text-right" : "text-left")}>
            {timestamp.toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
          
          {/* Show sources if available */}
          {!isUser && metadata?.sources && metadata.sources.length > 0 && (
            <div className="flex gap-1">
              {metadata.sources.map((source, idx) => (
                <Badge key={idx} variant="secondary" className="text-xs px-2 py-0 h-5">
                  {getSourceIcon(source)}
                  <span className="ml-1">{source}</span>
                </Badge>
              ))}
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <Avatar className="h-8 w-8 mt-1">
          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">You</AvatarFallback>
        </Avatar>
      )}
    </div>
  )
}