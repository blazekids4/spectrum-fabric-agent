import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { TrendingUp, Users, ClipboardPen, Search } from "lucide-react"

interface SuggestedPromptsProps {
  onSelectPrompt: (prompt: string) => void
}

const prompts = [
  {
    icon: <TrendingUp className="h-4 w-4" />,
    title: "Competitor Analysis",
    prompt: "What are the top competitor mentions in our call transcripts this week?"
  },
  {
    icon: <Users className="h-4 w-4" />,
    title: "Customer Switching",
    prompt: "Show me customer switching patterns between Charter and AT&T"
  },
  {
    icon: <ClipboardPen className="h-4 w-4" />,
    title: "Coaching Opportunities",
    prompt: "As VP of Customer Experience, what coaching opportunities can I identify from recent calls?"
  },
  {
    icon: <Search className="h-4 w-4" />,
    title: "Executive Summary",
    prompt: "As CEO of Charter, give me a summary of key insights from the latest customer calls"
  }
]

export function SuggestedPrompts({ onSelectPrompt }: SuggestedPromptsProps) {
  return (
    <div className="grid grid-cols-2 gap-2 p-4">
      {prompts.map((prompt, idx) => (
        <Card
          key={idx}
          className="p-3 cursor-pointer hover:bg-slate-200 transition-colors"
          onClick={() => onSelectPrompt(prompt.prompt)}
        >
          <div className="flex items-start gap-2">
            <div className="text-primary mt-0.5">{prompt.icon}</div>
            <div className="flex-1">
              <p className="text-sm text-blue-800  font-medium">{prompt.title}</p>
              <p className="text-xs text-blue-800 mt-0.5">{prompt.prompt}</p>
            </div>
          </div>
        </Card>
      ))}
    </div>
  )
}