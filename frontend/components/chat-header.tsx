import Image from "next/image"
import { Card } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

export function ChatHeader() {
  return (
    <Card className="border-b rounded-none bg-card/50 backdrop-blur-sm">
      <div className="flex items-center gap-3 p-4">
        <div className="relative">
          <Image
            src="/charter-logo.png"
            alt="Charter Communications"
            width={120}
            height={40}
            className="h-8 w-auto"
            priority
          />
        </div>

        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h1 className="font-semibold text-lg text-balance">VIP Assistant</h1>
            <Badge variant="secondary" className="text-xs">
              AI Powered
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">Your dedicated business intelligence agent</p>
        </div>

        <div className="flex items-center gap-1">
          <div className="h-2 w-2 bg-green-500 rounded-full animate-pulse"></div>
          <span className="text-xs text-muted-foreground">Online</span>
        </div>
      </div>
    </Card>
  )
}
