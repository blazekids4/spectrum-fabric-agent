import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { FileText, Database, Globe } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"
import { ComponentPropsWithoutRef } from "react"

// Define custom component props for ReactMarkdown components
type ComponentType = React.ElementType;
interface CodeProps extends ComponentPropsWithoutRef<"code"> {
  inline?: boolean;
  className?: string;
}

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
          <div className="text-pretty markdown-content">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Customize how code blocks are rendered
                code: ({ inline, className, children, ...props }: CodeProps) => {
                  const match = /language-(\w+)/.exec(className || '')
                  return !inline ? (
                    <pre className="bg-muted/50 p-2 rounded overflow-x-auto text-[13px] my-2">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  ) : (
                    <code className="bg-muted/50 px-1 py-0.5 rounded text-[13px]" {...props}>
                      {children}
                    </code>
                  )
                },
                // Customize headings
                h1: (props) => <h1 className="text-xl font-bold mt-4 mb-2" {...props} />,
                h2: (props) => <h2 className="text-lg font-bold mt-3 mb-2" {...props} />,
                h3: (props) => <h3 className="text-md font-bold mt-2 mb-1" {...props} />,
                // Customize links
                a: (props) => <a className="text-primary underline" {...props} />,
                // Customize lists
                ul: (props) => <ul className="my-2 ml-4 list-disc" {...props} />,
                ol: (props) => <ol className="my-2 ml-4 list-decimal" {...props} />,
                li: (props) => <li className="my-1" {...props} />,
                // Customize tables
                table: (props) => <table className="border-collapse my-2 table-auto" {...props} />,
                th: (props) => <th className="border border-gray-300 px-4 py-2 text-left font-bold bg-muted/30" {...props} />,
                td: (props) => <td className="border border-gray-300 px-4 py-2" {...props} />,
                // Customize blockquotes
                blockquote: (props) => <blockquote className="border-l-4 border-muted pl-4 italic my-2" {...props} />,
                // Customize paragraphs
                p: (props) => <p className="my-2" {...props} />,
              }}
            >
              {message}
            </ReactMarkdown>
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