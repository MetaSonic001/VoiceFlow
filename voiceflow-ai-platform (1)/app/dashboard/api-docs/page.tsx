"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import {
  Code,
  Copy,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  Play,
  Book,
  Zap,
  Shield,
  Database,
  MessageSquare,
  Phone,
  Settings,
  Users,
  BarChart3
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface APIEndpoint {
  id: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'
  path: string
  description: string
  category: string
  parameters?: {
    name: string
    type: string
    required: boolean
    description: string
  }[]
  requestBody?: {
    type: string
    example: any
  }
  responses: {
    status: number
    description: string
    example?: any
  }[]
  authentication: boolean
}

interface APICategory {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  endpoints: APIEndpoint[]
}

export default function APIDocumentationPage() {
  const [categories, setCategories] = useState<APICategory[]>([])
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null)
  const [copiedCode, setCopiedCode] = useState<string | null>(null)

  useEffect(() => {
    loadAPIDocumentation()
  }, [])

  const loadAPIDocumentation = async () => {
    try {
      // This would call an API documentation endpoint
      // const data = await apiClient.getAPIDocumentation()
      // For now, using mock data
      const mockCategories: APICategory[] = [
        {
          id: 'authentication',
          name: 'Authentication',
          description: 'User authentication and authorization endpoints',
          icon: <Shield className="w-5 h-5" />,
          endpoints: [
            {
              id: 'auth-login',
              method: 'POST',
              path: '/api/auth/login',
              description: 'Authenticate user and return JWT token',
              category: 'authentication',
              parameters: [],
              requestBody: {
                type: 'application/json',
                example: {
                  email: 'user@example.com',
                  password: 'password123'
                }
              },
              responses: [
                {
                  status: 200,
                  description: 'Authentication successful',
                  example: {
                    token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
                    user: {
                      id: 'user-123',
                      email: 'user@example.com',
                      name: 'John Doe'
                    }
                  }
                },
                {
                  status: 401,
                  description: 'Invalid credentials',
                  example: {
                    error: 'Invalid email or password'
                  }
                }
              ],
              authentication: false
            },
            {
              id: 'auth-me',
              method: 'GET',
              path: '/api/auth/me',
              description: 'Get current user information',
              category: 'authentication',
              responses: [
                {
                  status: 200,
                  description: 'User information retrieved',
                  example: {
                    id: 'user-123',
                    email: 'user@example.com',
                    name: 'John Doe',
                    role: 'admin'
                  }
                }
              ],
              authentication: true
            }
          ]
        },
        {
          id: 'agents',
          name: 'Agents',
          description: 'AI agent management and configuration',
          icon: <Zap className="w-5 h-5" />,
          endpoints: [
            {
              id: 'agents-list',
              method: 'GET',
              path: '/api/agents',
              description: 'List all agents with pagination and filtering',
              category: 'agents',
              parameters: [
                { name: 'page', type: 'integer', required: false, description: 'Page number (default: 1)' },
                { name: 'limit', type: 'integer', required: false, description: 'Items per page (default: 10)' },
                { name: 'status', type: 'string', required: false, description: 'Filter by status (active, inactive)' },
                { name: 'search', type: 'string', required: false, description: 'Search by name or description' }
              ],
              responses: [
                {
                  status: 200,
                  description: 'Agents retrieved successfully',
                  example: {
                    agents: [
                      {
                        id: 'agent-123',
                        name: 'Customer Support Bot',
                        description: 'Handles customer inquiries',
                        status: 'active',
                        createdAt: '2024-01-15T10:00:00Z'
                      }
                    ],
                    pagination: {
                      page: 1,
                      limit: 10,
                      total: 25,
                      pages: 3
                    }
                  }
                }
              ],
              authentication: true
            },
            {
              id: 'agents-create',
              method: 'POST',
              path: '/api/agents',
              description: 'Create a new AI agent',
              category: 'agents',
              requestBody: {
                type: 'application/json',
                example: {
                  name: 'Sales Assistant',
                  description: 'Helps with sales inquiries',
                  configuration: {
                    model: 'gpt-4',
                    temperature: 0.7,
                    maxTokens: 1000
                  }
                }
              },
              responses: [
                {
                  status: 201,
                  description: 'Agent created successfully',
                  example: {
                    id: 'agent-456',
                    name: 'Sales Assistant',
                    status: 'inactive',
                    createdAt: '2024-01-15T11:00:00Z'
                  }
                }
              ],
              authentication: true
            }
          ]
        },
        {
          id: 'conversations',
          name: 'Conversations',
          description: 'Chat conversation management',
          icon: <MessageSquare className="w-5 h-5" />,
          endpoints: [
            {
              id: 'conversations-list',
              method: 'GET',
              path: '/api/conversations',
              description: 'List user conversations',
              category: 'conversations',
              responses: [
                {
                  status: 200,
                  description: 'Conversations retrieved',
                  example: {
                    conversations: [
                      {
                        id: 'conv-123',
                        userId: 'user-123',
                        agentId: 'agent-123',
                        status: 'active',
                        createdAt: '2024-01-15T10:00:00Z',
                        lastMessageAt: '2024-01-15T10:30:00Z'
                      }
                    ]
                  }
                }
              ],
              authentication: true
            }
          ]
        },
        {
          id: 'analytics',
          name: 'Analytics',
          description: 'Usage analytics and reporting',
          icon: <BarChart3 className="w-5 h-5" />,
          endpoints: [
            {
              id: 'analytics-overview',
              method: 'GET',
              path: '/api/analytics/overview',
              description: 'Get analytics overview data',
              category: 'analytics',
              parameters: [
                { name: 'period', type: 'string', required: false, description: 'Time period (7d, 30d, 90d)' }
              ],
              responses: [
                {
                  status: 200,
                  description: 'Analytics data retrieved',
                  example: {
                    totalUsers: 1250,
                    activeUsers: 890,
                    totalConversations: 5432,
                    avgResponseTime: 2.3,
                    satisfactionScore: 4.2
                  }
                }
              ],
              authentication: true
            }
          ]
        }
      ]
      setCategories(mockCategories)
    } catch (error) {
      console.error('Failed to load API documentation:', error)
    }
  }

  const copyToClipboard = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedCode(id)
      setTimeout(() => setCopiedCode(null), 2000)
    } catch (error) {
      console.error('Failed to copy to clipboard:', error)
    }
  }

  const getMethodColor = (method: string) => {
    switch (method) {
      case 'GET': return 'bg-green-100 text-green-800'
      case 'POST': return 'bg-blue-100 text-blue-800'
      case 'PUT': return 'bg-yellow-100 text-yellow-800'
      case 'DELETE': return 'bg-red-100 text-red-800'
      case 'PATCH': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const generateCurlExample = (endpoint: APIEndpoint) => {
    const baseUrl = 'https://api.voiceflow.com'
    let curl = `curl -X ${endpoint.method} "${baseUrl}${endpoint.path}"`

    if (endpoint.authentication) {
      curl += ` \\\n  -H "Authorization: Bearer YOUR_JWT_TOKEN"`
    }

    if (endpoint.requestBody) {
      curl += ` \\\n  -H "Content-Type: ${endpoint.requestBody.type}" \\\n  -d '${JSON.stringify(endpoint.requestBody.example, null, 2)}'`
    }

    return curl
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">API Documentation</h1>
                <p className="text-muted-foreground">Complete reference for VoiceFlow API endpoints</p>
              </div>
              <div className="flex space-x-2">
                <Button variant="outline">
                  <ExternalLink className="w-4 h-4 mr-2" />
                  OpenAPI Spec
                </Button>
                <Button variant="outline">
                  <Book className="w-4 h-4 mr-2" />
                  SDK Docs
                </Button>
              </div>
            </div>

            <div className="grid lg:grid-cols-4 gap-6">
              {/* API Categories Sidebar */}
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">API Reference</CardTitle>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="space-y-1">
                      {categories.map((category) => (
                        <Collapsible key={category.id}>
                          <CollapsibleTrigger className="w-full p-3 text-left hover:bg-muted/50 flex items-center space-x-3">
                            {category.icon}
                            <span className="font-medium">{category.name}</span>
                            <ChevronRight className="w-4 h-4 ml-auto" />
                          </CollapsibleTrigger>
                          <CollapsibleContent className="pl-8 space-y-1">
                            {category.endpoints.map((endpoint) => (
                              <button
                                key={endpoint.id}
                                onClick={() => setSelectedEndpoint(endpoint.id)}
                                className={`w-full p-2 text-left text-sm hover:bg-muted/50 rounded flex items-center space-x-2 ${
                                  selectedEndpoint === endpoint.id ? 'bg-muted' : ''
                                }`}
                              >
                                <Badge className={`text-xs ${getMethodColor(endpoint.method)}`}>
                                  {endpoint.method}
                                </Badge>
                                <span className="truncate">{endpoint.path}</span>
                              </button>
                            ))}
                          </CollapsibleContent>
                        </Collapsible>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* API Documentation Content */}
              <div className="lg:col-span-3">
                {selectedEndpoint ? (
                  (() => {
                    const endpoint = categories
                      .flatMap(cat => cat.endpoints)
                      .find(ep => ep.id === selectedEndpoint)

                    if (!endpoint) return null

                    return (
                      <div className="space-y-6">
                        {/* Endpoint Header */}
                        <Card>
                          <CardHeader>
                            <div className="flex items-center space-x-3">
                              <Badge className={getMethodColor(endpoint.method)}>
                                {endpoint.method}
                              </Badge>
                              <code className="text-lg font-mono">{endpoint.path}</code>
                            </div>
                            <CardTitle>{endpoint.description}</CardTitle>
                            <div className="flex items-center space-x-4 text-sm text-muted-foreground">
                              <span className="flex items-center">
                                <Shield className="w-4 h-4 mr-1" />
                                {endpoint.authentication ? 'Requires Authentication' : 'Public'}
                              </span>
                              <span>Category: {endpoint.category}</span>
                            </div>
                          </CardHeader>
                        </Card>

                        <Tabs defaultValue="overview" className="w-full">
                          <TabsList>
                            <TabsTrigger value="overview">Overview</TabsTrigger>
                            <TabsTrigger value="parameters">Parameters</TabsTrigger>
                            <TabsTrigger value="request">Request</TabsTrigger>
                            <TabsTrigger value="responses">Responses</TabsTrigger>
                            <TabsTrigger value="examples">Examples</TabsTrigger>
                          </TabsList>

                          <TabsContent value="overview" className="space-y-4">
                            <Card>
                              <CardHeader>
                                <CardTitle>Description</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <p>{endpoint.description}</p>
                              </CardContent>
                            </Card>
                          </TabsContent>

                          <TabsContent value="parameters" className="space-y-4">
                            <Card>
                              <CardHeader>
                                <CardTitle>Query Parameters</CardTitle>
                              </CardHeader>
                              <CardContent>
                                {endpoint.parameters && endpoint.parameters.length > 0 ? (
                                  <div className="space-y-3">
                                    {endpoint.parameters.map((param) => (
                                      <div key={param.name} className="border rounded p-3">
                                        <div className="flex items-center space-x-2 mb-1">
                                          <code className="font-mono text-sm">{param.name}</code>
                                          <Badge variant="outline">{param.type}</Badge>
                                          {param.required && <Badge variant="destructive">Required</Badge>}
                                        </div>
                                        <p className="text-sm text-muted-foreground">{param.description}</p>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-muted-foreground">No query parameters required</p>
                                )}
                              </CardContent>
                            </Card>
                          </TabsContent>

                          <TabsContent value="request" className="space-y-4">
                            <Card>
                              <CardHeader>
                                <CardTitle>Request Body</CardTitle>
                              </CardHeader>
                              <CardContent>
                                {endpoint.requestBody ? (
                                  <div className="space-y-3">
                                    <div className="flex items-center space-x-2">
                                      <span className="text-sm font-medium">Content-Type:</span>
                                      <code className="text-sm">{endpoint.requestBody.type}</code>
                                    </div>
                                    <div>
                                      <h4 className="font-medium mb-2">Example:</h4>
                                      <pre className="bg-muted p-3 rounded text-sm overflow-x-auto">
                                        {JSON.stringify(endpoint.requestBody.example, null, 2)}
                                      </pre>
                                    </div>
                                  </div>
                                ) : (
                                  <p className="text-muted-foreground">No request body required</p>
                                )}
                              </CardContent>
                            </Card>
                          </TabsContent>

                          <TabsContent value="responses" className="space-y-4">
                            <Card>
                              <CardHeader>
                                <CardTitle>Response Codes</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="space-y-4">
                                  {endpoint.responses.map((response) => (
                                    <div key={response.status} className="border rounded p-4">
                                      <div className="flex items-center space-x-2 mb-2">
                                        <Badge variant={response.status >= 200 && response.status < 300 ? 'default' : 'destructive'}>
                                          {response.status}
                                        </Badge>
                                        <span className="font-medium">{response.description}</span>
                                      </div>
                                      {response.example && (
                                        <div>
                                          <h5 className="font-medium mb-2">Example Response:</h5>
                                          <pre className="bg-muted p-3 rounded text-sm overflow-x-auto">
                                            {JSON.stringify(response.example, null, 2)}
                                          </pre>
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              </CardContent>
                            </Card>
                          </TabsContent>

                          <TabsContent value="examples" className="space-y-4">
                            <Card>
                              <CardHeader>
                                <CardTitle>cURL Example</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="relative">
                                  <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
                                    {generateCurlExample(endpoint)}
                                  </pre>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="absolute top-2 right-2"
                                    onClick={() => copyToClipboard(generateCurlExample(endpoint), `curl-${endpoint.id}`)}
                                  >
                                    <Copy className="w-4 h-4" />
                                    {copiedCode === `curl-${endpoint.id}` ? 'Copied!' : 'Copy'}
                                  </Button>
                                </div>
                              </CardContent>
                            </Card>

                            <Card>
                              <CardHeader>
                                <CardTitle>JavaScript Example</CardTitle>
                              </CardHeader>
                              <CardContent>
                                <div className="relative">
                                  <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
{`// Using fetch
const response = await fetch('${endpoint.path}', {
  method: '${endpoint.method}',
  headers: {
    'Content-Type': 'application/json'${endpoint.authentication ? ",\n    'Authorization': 'Bearer YOUR_JWT_TOKEN'" : ''}
  }${endpoint.requestBody ? `,\n  body: JSON.stringify(${JSON.stringify(endpoint.requestBody.example, null, 2)})` : ''}
});

const data = await response.json();`}
                                  </pre>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    className="absolute top-2 right-2"
                                    onClick={() => copyToClipboard(`// Using fetch
const response = await fetch('${endpoint.path}', {
  method: '${endpoint.method}',
  headers: {
    'Content-Type': 'application/json'${endpoint.authentication ? ",\n    'Authorization': 'Bearer YOUR_JWT_TOKEN'" : ''}
  }${endpoint.requestBody ? `,\n  body: JSON.stringify(${JSON.stringify(endpoint.requestBody.example, null, 2)})` : ''}
});

const data = await response.json();`, `js-${endpoint.id}`)}
                                  >
                                    <Copy className="w-4 h-4" />
                                    {copiedCode === `js-${endpoint.id}` ? 'Copied!' : 'Copy'}
                                  </Button>
                                </div>
                              </CardContent>
                            </Card>
                          </TabsContent>
                        </Tabs>
                      </div>
                    )
                  })()
                ) : (
                  <Card>
                    <CardContent className="p-12 text-center">
                      <Code className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                      <h3 className="text-lg font-medium mb-2">Select an API Endpoint</h3>
                      <p className="text-muted-foreground">
                        Choose an endpoint from the sidebar to view detailed documentation and examples.
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </div>
        </div>
     
    )
  }