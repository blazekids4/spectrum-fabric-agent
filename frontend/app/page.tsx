import { ChatInterface } from "@/components/chat-interface"
import Image from "next/image"

export default function Home() {
  return (
    <main className="bg-gradient-to-br from-background via-background to-muted/20 p-4 mt-10 flex items-center justify-center">
      <div className="w-full max-w-4xl">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-4">
            <Image
              src="/spec_large.png"
              alt="Spectrum VIP Assistant Logo"
              width={120}
              height={120}
              className="object-contain"
              priority
            />
          </div>
          <h1 className="text-3xl font-bold text-balance mb-2 text-slate-900">
            AI-Leen
          </h1>
          <p className="text-muted-foreground text-pretty max-w-2xl mx-auto">
            AI-powered customer intelligence
          </p>
        </div>

        <ChatInterface />
        
        <div className="mt-4 text-center">
          <p className="text-xs text-muted-foreground">
            Powered by Microsoft Fabric Data Agents & Azure AI
          </p>
        </div>
      </div>
    </main>
  )
}