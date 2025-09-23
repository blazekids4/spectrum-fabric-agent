import { NextRequest, NextResponse } from 'next/server'

const PYTHON_API_URL = process.env.PYTHON_API_URL || 'http://localhost:5328'

export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  return proxyRequest(request, 'GET', path)
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/')
  return proxyRequest(request, 'POST', path)
}

async function proxyRequest(request: NextRequest, method: string, path: string) {
  try {
    const url = `${PYTHON_API_URL}/${path}${request.nextUrl.search}`
    const body = method !== 'GET' ? await request.text() : undefined
    
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': request.headers.get('content-type') || 'application/json',
      },
      body,
    })
    
    const data = await response.text()
    
    return new NextResponse(data, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('content-type') || 'application/json',
      },
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal Server Error' },
      { status: 500 }
    )
  }
}