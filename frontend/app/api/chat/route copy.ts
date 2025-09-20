import { type NextRequest, NextResponse } from "next/server"

// Proxy to local FastAPI Fabric Agent Service. Configure with NEXT_PUBLIC_FABRIC_AGENT_URL
const BACKEND_URL = process.env.NEXT_PUBLIC_FABRIC_AGENT_URL || "http://127.0.0.1:8001/chat"

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    // Forward to Fabric Agent Service
    const resp = await fetch(BACKEND_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })

    if (!resp.ok) {
      const text = await resp.text()
      console.error("Fabric agent service error:", text)
      return NextResponse.json({ error: "Agent service error", detail: text }, { status: 502 })
    }

    const data = await resp.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error("Chat API proxy error:", error)
    return NextResponse.json({ error: "Failed to proxy chat message" }, { status: 500 })
  }
}
