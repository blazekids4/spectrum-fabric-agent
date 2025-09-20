import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card } from "@/components/ui/card"

interface ChatMessageProps {
  message: string
  isUser: boolean
  timestamp: Date
}

export function ChatMessage({ message, isUser, timestamp }: ChatMessageProps) {
  return (
    <div className={cn("flex gap-3 mb-4", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <Avatar className="h-8 w-8 mt-1">
          <AvatarImage src="/icon.png" alt="Charter VIP" />
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
             * Simple renderer:
             * - Split on triple-backtick code fences ``` and render code blocks inside <pre><code>
             * - Preserve other text newlines by replacing with <br />
             * This avoids pulling a full markdown parser but improves readability for code/stack traces.
             */}
            {message.split(/```(?:\w+)?\n?/).map((part, idx) => {
              // Odd indices are code blocks when splitting on fences
              const isCode = idx % 2 === 1
              if (isCode) {
                return (
                  <pre key={idx} className="bg-muted p-2 rounded overflow-x-auto text-[13px]">
                    <code>{part}</code>
                  </pre>
                )
              }

              // Non-code text: preserve newlines
              return (
                <p key={idx} className="whitespace-pre-wrap">
                  {part}
                </p>
              )
            })}
          </div>
        </Card>

        <p className={cn("text-xs text-muted-foreground px-1", isUser ? "text-right" : "text-left")}>
          {timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>

      {isUser && (
        <Avatar className="h-8 w-8 mt-1">
          <AvatarFallback className="bg-secondary text-secondary-foreground text-xs">You</AvatarFallback>
        </Avatar>
      )}
    </div>
  )
}
