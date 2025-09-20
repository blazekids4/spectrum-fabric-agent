import { ChatInterface } from "@/components/chat-interface"

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20 p-4 flex items-center justify-center">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-balance mb-2 charter-text-gradient">Charter VIP Assistant</h1>
          <p className="text-muted-foreground text-pretty">
            Premium AI-powered support for Charter Communications Executives
          </p>
        </div>

        <ChatInterface />
      </div>
    </main>
  )
}
