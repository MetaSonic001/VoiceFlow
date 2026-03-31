"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import {
  Search,
  Upload,
  FileText,
  Image,
  Video,
  Music,
  Archive,
  Trash2,
  Download,
  Eye,
  Filter,
  Grid,
  List,
  Folder,
  Globe,
  Building2,
  Loader2,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Tag,
  Briefcase,
  Link,
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Document {
  id: string
  name: string
  type: 'pdf' | 'docx' | 'txt' | 'image' | 'video' | 'audio' | 'other'
  size: number
  uploadedAt: string
  lastModified: string
  status: 'processing' | 'ready' | 'error'
  tags: string[]
  category: string
  description?: string
  thumbnail?: string
}

interface Category {
  id: string
  name: string
  count: number
  color: string
}

export default function KnowledgeBasePage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedType, setSelectedType] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null)
  const [showUploadDialog, setShowUploadDialog] = useState(false)
  const [loading, setLoading] = useState(true)

// Company profile (structured onboarding data from Postgres)
  const [companyProfile, setCompanyProfile] = useState<{
    company_name: string | null
    industry: string | null
    use_case: string | null
    website_url: string | null
    description: string | null
  } | null>(null)
  const [profileLoading, setProfileLoading] = useState(true)

  // Company knowledge (scraped from company website during onboarding)
  const [companyChunks, setCompanyChunks] = useState<Array<{ id: string; content: string; metadata: any }>>([])
  const [companyKbLoading, setCompanyKbLoading] = useState(true)
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set())
  const [deletingChunk, setDeletingChunk] = useState<string | null>(null)

  // URL ingestion
  const [urlInput, setUrlInput] = useState('')
  const [ingestJobId, setIngestJobId] = useState<string | null>(null)
  const [ingestStatus, setIngestStatus] = useState<'idle' | 'submitting' | 'processing' | 'completed' | 'failed'>('idle')
  const [ingestProgress, setIngestProgress] = useState(0)
  const [ingestChunks, setIngestChunks] = useState(0)

  useEffect(() => {
    loadDocuments()
    loadCategories()
    loadCompanyKnowledge()
    loadCompanyProfile()
  }, [])

  const loadCompanyProfile = async () => {
    try {
      setProfileLoading(true)
      const data = await apiClient.getCompanyProfile()
      setCompanyProfile(data)
    } catch {
      setCompanyProfile(null)
    } finally {
      setProfileLoading(false)
    }
  }

  const loadCompanyKnowledge = async () => {
    try {
      setCompanyKbLoading(true)
      const data = await apiClient.getCompanyKnowledge()
      setCompanyChunks(data.chunks || [])
    } catch {
      setCompanyChunks([])
    } finally {
      setCompanyKbLoading(false)
    }
  }

  const handleDeleteChunk = async (chunkId: string) => {
    setDeletingChunk(chunkId)
    try {
      await apiClient.deleteCompanyKnowledge(chunkId)
      setCompanyChunks((prev) => prev.filter((c) => c.id !== chunkId))
    } catch {
      // ignore
    } finally {
      setDeletingChunk(null)
    }
  }

  const submitUrlIngestion = async () => {
    const trimmed = urlInput.trim()
    if (!trimmed) return
    try {
      setIngestStatus('submitting')
      const result = await apiClient.triggerUrlIngestion(trimmed)
      setIngestJobId(result.jobId)
      setIngestStatus('processing')
      setIngestProgress(0)
      setIngestChunks(0)
    } catch {
      setIngestStatus('failed')
    }
  }

  // Poll ingestion status while a job is running
  useEffect(() => {
    if (!ingestJobId || ingestStatus !== 'processing') return
    const interval = setInterval(async () => {
      try {
        const s = await apiClient.getIngestionStatus(ingestJobId)
        setIngestProgress(Number(s.progress) || 0)
        setIngestChunks(s.chunks_processed ?? 0)
        if (s.status === 'completed') {
          setIngestStatus('completed')
          clearInterval(interval)
          loadDocuments()
        } else if (s.status?.startsWith('failed')) {
          setIngestStatus('failed')
          clearInterval(interval)
        }
      } catch {
        // network blip — keep polling
      }
    }, 3000)
    return () => clearInterval(interval)
  }, [ingestJobId, ingestStatus])

  const toggleExpand = (id: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const loadDocuments = async () => {
    try {
      setLoading(true)
      const data = await apiClient.getKnowledgeBase()
      setDocuments(data)
    } catch (error) {
      console.error('Error loading documents:', error)
      // Fallback to mock data
      const mockDocuments: Document[] = [
        {
          id: 'doc-001',
          name: 'User Manual.pdf',
          type: 'pdf',
          size: 2048576, // 2MB
          uploadedAt: '2024-01-15T10:00:00Z',
          lastModified: '2024-01-15T10:00:00Z',
          status: 'ready',
          tags: ['manual', 'user-guide', 'documentation'],
          category: 'Documentation',
          description: 'Complete user manual for the platform'
        },
        {
          id: 'doc-002',
          name: 'API Reference.docx',
          type: 'docx',
          size: 1048576, // 1MB
          uploadedAt: '2024-01-14T15:30:00Z',
          lastModified: '2024-01-14T16:00:00Z',
          status: 'ready',
          tags: ['api', 'reference', 'technical'],
          category: 'Technical',
          description: 'Comprehensive API documentation'
        }
      ]
      setDocuments(mockDocuments)
    } finally {
      setLoading(false)
    }
  }
  const loadCategories = async () => {
    try {
      // This would call a categories API endpoint
      // const data = await apiClient.getDocumentCategories()
      // For now, using mock data
      const mockCategories: Category[] = [
        { id: 'all', name: 'All Documents', count: 5, color: 'gray' },
        { id: 'documentation', name: 'Documentation', count: 2, color: 'blue' },
        { id: 'technical', name: 'Technical', count: 1, color: 'green' },
        { id: 'media', name: 'Media', count: 1, color: 'purple' },
        { id: 'training', name: 'Training', count: 1, color: 'orange' },
        { id: 'support', name: 'Support', count: 1, color: 'red' }
      ]
      setCategories(mockCategories)
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'pdf': return <FileText className="w-8 h-8 text-red-500" />
      case 'docx': return <FileText className="w-8 h-8 text-blue-500" />
      case 'txt': return <FileText className="w-8 h-8 text-gray-500" />
      case 'image': return <Image className="w-8 h-8 text-green-500" />
      case 'video': return <Video className="w-8 h-8 text-purple-500" />
      case 'audio': return <Music className="w-8 h-8 text-orange-500" />
      default: return <Archive className="w-8 h-8 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'ready': return 'default'
      case 'processing': return 'secondary'
      case 'error': return 'destructive'
      default: return 'outline'
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const filteredDocuments = documents.filter(doc => {
    const matchesSearch = doc.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         doc.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         doc.tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))

    const matchesCategory = selectedCategory === 'all' || doc.category.toLowerCase() === selectedCategory.toLowerCase()
    const matchesType = selectedType === 'all' || doc.type === selectedType

    return matchesSearch && matchesCategory && matchesType
  })

  const handleUpload = async (files: FileList) => {
    // This would handle file upload to the backend
    console.log('Uploading files:', files)
    setShowUploadDialog(false)
    // Refresh documents after upload
    loadDocuments()
  }

  const handleDelete = async (documentId: string) => {
    try {
      // This would call a delete document API endpoint
      // await apiClient.deleteDocument(documentId)
      setDocuments(prev => prev.filter(doc => doc.id !== documentId))
    } catch (error) {
      console.error('Failed to delete document:', error)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-2">Loading knowledge base...</span>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Knowledge Base</h1>
                <p className="text-muted-foreground">Manage documents and training materials</p>
              </div>
              <Dialog open={showUploadDialog} onOpenChange={setShowUploadDialog}>
                <DialogTrigger asChild>
                  <Button>
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Documents
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Upload Documents</DialogTitle>
                    <DialogDescription>
                      Upload files to add them to your knowledge base. Supported formats: PDF, DOCX, TXT, images, videos, and archives.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="space-y-4">
                    <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                      <Upload className="w-8 h-8 mx-auto text-gray-400 mb-2" />
                      <p className="text-sm text-gray-600 mb-2">Drag and drop files here, or click to browse</p>
                      <input
                        type="file"
                        multiple
                        accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.mp4,.avi,.mp3,.wav,.zip"
                        className="hidden"
                        id="file-upload"
                        onChange={(e) => e.target.files && handleUpload(e.target.files)}
                      />
                      <label htmlFor="file-upload">
                        <Button variant="outline" className="cursor-pointer">
                          Browse Files
                        </Button>
                      </label>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      Maximum file size: 100MB per file. Files will be processed for search and AI training.
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>

            {/* ── Company Profile (from onboarding Postgres record) ── */}
            {(companyProfile?.company_name || profileLoading) && (
              <Card className="mb-4 border-primary/20 bg-primary/5">
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-primary" />
                    <CardTitle className="text-lg">Company Profile</CardTitle>
                    {profileLoading && <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />}
                  </div>
                  <CardDescription>
                    Your company details set during onboarding. This profile is stored in the vector database and used to personalise every AI agent response.
                  </CardDescription>
                </CardHeader>
                {!profileLoading && companyProfile && (
                  <CardContent>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                      {companyProfile.company_name && (
                        <div className="flex items-start gap-2">
                          <Building2 className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-muted-foreground">Company</p>
                            <p className="font-medium">{companyProfile.company_name}</p>
                          </div>
                        </div>
                      )}
                      {companyProfile.industry && (
                        <div className="flex items-start gap-2">
                          <Tag className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-muted-foreground">Industry</p>
                            <p className="font-medium capitalize">{companyProfile.industry.replace(/-/g, ' ')}</p>
                          </div>
                        </div>
                      )}
                      {companyProfile.use_case && (
                        <div className="flex items-start gap-2">
                          <Briefcase className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-muted-foreground">Primary Use Case</p>
                            <p className="font-medium capitalize">{companyProfile.use_case.replace(/-/g, ' ')}</p>
                          </div>
                        </div>
                      )}
                      {companyProfile.website_url && (
                        <div className="flex items-start gap-2">
                          <Link className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-muted-foreground">Website</p>
                            <a
                              href={companyProfile.website_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="font-medium text-primary hover:underline truncate block max-w-[200px]"
                            >
                              {companyProfile.website_url.replace(/^https?:\/\//, '')}
                            </a>
                          </div>
                        </div>
                      )}
                      {companyProfile.description && (
                        <div className="flex items-start gap-2 sm:col-span-2">
                          <Globe className="w-4 h-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                          <div>
                            <p className="text-xs text-muted-foreground">Description</p>
                            <p className="text-muted-foreground leading-relaxed">{companyProfile.description}</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                )}
              </Card>
            )}

            {/* ── Company Knowledge (scraped during onboarding) ── */}
            <Card className="mb-6 border-primary/20">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-5 h-5 text-primary" />
                    <CardTitle className="text-lg">Company Knowledge</CardTitle>
                    <Badge variant="secondary" className="text-xs">
                      {companyChunks.length} chunks
                    </Badge>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={loadCompanyKnowledge}
                    disabled={companyKbLoading}
                  >
                    <RefreshCw className={`w-4 h-4 ${companyKbLoading ? "animate-spin" : ""}`} />
                  </Button>
                </div>
                <CardDescription>
                  Content automatically scraped from your company website during onboarding. This is loaded into every agent's knowledge base.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {companyKbLoading ? (
                  <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Loading company knowledge…
                  </div>
                ) : companyChunks.length === 0 ? (
                  <div className="text-center py-8 text-muted-foreground text-sm space-y-2">
                    <Globe className="w-8 h-8 mx-auto opacity-30" />
                    <p>No company knowledge yet.</p>
                    <p className="text-xs">Complete the company onboarding step with a website URL to auto-scrape your company's information.</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {companyChunks.map((chunk) => {
                      const isExpanded = expandedChunks.has(chunk.id)
                      const preview = chunk.content.slice(0, 160)
                      const needsTruncation = chunk.content.length > 160
                      return (
                        <div key={chunk.id} className="rounded-lg border border-border/60 bg-muted/30 p-3 group">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1 flex-wrap">
                                <Globe className="w-3 h-3 text-muted-foreground flex-shrink-0" />
                                <span className="text-xs text-muted-foreground truncate max-w-[240px]">
                                  {chunk.metadata?.source || "—"}
                                </span>
                                <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                                  chunk {(chunk.metadata?.chunk ?? 0) + 1}
                                </Badge>
                              </div>
                              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                                {isExpanded ? chunk.content : preview}
                                {!isExpanded && needsTruncation && (
                                  <span className="text-muted-foreground">…</span>
                                )}
                              </p>
                              {needsTruncation && (
                                <button
                                  onClick={() => toggleExpand(chunk.id)}
                                  className="text-xs text-primary mt-1 flex items-center gap-0.5 hover:underline"
                                >
                                  {isExpanded ? (
                                    <><ChevronUp className="w-3 h-3" /> Show less</>
                                  ) : (
                                    <><ChevronDown className="w-3 h-3" /> Show more</>
                                  )}
                                </button>
                              )}
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0"
                              disabled={deletingChunk === chunk.id}
                              onClick={() => handleDeleteChunk(chunk.id)}
                            >
                              {deletingChunk === chunk.id
                                ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                : <Trash2 className="w-3.5 h-3.5" />
                              }
                            </Button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* ── Add URL to Knowledge Base ── */}
            <Card className="mb-6">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-2">
                  <Globe className="w-5 h-5 text-primary" />
                  <CardTitle className="text-lg">Add URL to Knowledge Base</CardTitle>
                </div>
                <CardDescription>
                  Paste any public URL and the scraper will extract its content and add it to the knowledge base.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <Input
                    placeholder="https://example.com/page"
                    value={urlInput}
                    onChange={(e) => setUrlInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && ingestStatus !== 'submitting' && ingestStatus !== 'processing' && submitUrlIngestion()}
                    disabled={ingestStatus === 'submitting' || ingestStatus === 'processing'}
                    className="flex-1"
                  />
                  <Button
                    onClick={submitUrlIngestion}
                    disabled={!urlInput.trim() || ingestStatus === 'submitting' || ingestStatus === 'processing'}
                  >
                    {ingestStatus === 'submitting' || ingestStatus === 'processing'
                      ? <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      : <Globe className="w-4 h-4 mr-2" />
                    }
                    {ingestStatus === 'processing' ? 'Scraping…' : 'Scrape & Add'}
                  </Button>
                </div>
                {ingestStatus === 'processing' && (
                  <div className="mt-3 space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>Scraping in progress…</span>
                      <span>{ingestProgress}% · {ingestChunks} chunks</span>
                    </div>
                    <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary transition-all duration-500 rounded-full"
                        style={{ width: `${ingestProgress}%` }}
                      />
                    </div>
                  </div>
                )}
                {ingestStatus === 'completed' && (
                  <p className="mt-2 text-xs text-green-600 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" /> Scraping complete — {ingestChunks} chunks added.{' '}
                    <button className="underline" onClick={() => { setIngestStatus('idle'); setUrlInput(''); setIngestJobId(null); }}>
                      Add another
                    </button>
                  </p>
                )}
                {ingestStatus === 'failed' && (
                  <p className="mt-2 text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" /> Scraping failed. Check the URL and try again.{' '}
                    <button className="underline" onClick={() => setIngestStatus('idle')}>Retry</button>
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Filters and Search */}
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="flex flex-col md:flex-row gap-4">
                  <div className="flex-1">
                    <div className="relative">
                      <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search documents..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                    <SelectTrigger className="w-full md:w-48">
                      <SelectValue placeholder="Category" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map((category) => (
                        <SelectItem key={category.id} value={category.id}>
                          <div className="flex items-center space-x-2">
                            <Folder className="w-4 h-4" />
                            <span>{category.name}</span>
                            <Badge variant="secondary" className="ml-auto">
                              {category.count}
                            </Badge>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select value={selectedType} onValueChange={setSelectedType}>
                    <SelectTrigger className="w-full md:w-32">
                      <SelectValue placeholder="Type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="pdf">PDF</SelectItem>
                      <SelectItem value="docx">DOCX</SelectItem>
                      <SelectItem value="txt">TXT</SelectItem>
                      <SelectItem value="image">Image</SelectItem>
                      <SelectItem value="video">Video</SelectItem>
                      <SelectItem value="audio">Audio</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                  <div className="flex border rounded-md">
                    <Button
                      variant={viewMode === 'grid' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setViewMode('grid')}
                      className="rounded-r-none"
                    >
                      <Grid className="w-4 h-4" />
                    </Button>
                    <Button
                      variant={viewMode === 'list' ? 'default' : 'ghost'}
                      size="sm"
                      onClick={() => setViewMode('list')}
                      className="rounded-l-none"
                    >
                      <List className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Categories Overview */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
              {categories.slice(1).map((category) => (
                <Card
                  key={category.id}
                  className={`cursor-pointer transition-colors hover:bg-muted/50 ${
                    selectedCategory === category.id ? 'ring-2 ring-primary' : ''
                  }`}
                  onClick={() => setSelectedCategory(category.id)}
                >
                  <CardContent className="p-4 text-center">
                    <Folder className={`w-8 h-8 mx-auto mb-2 text-${category.color}-500`} />
                    <h3 className="font-medium text-sm">{category.name}</h3>
                    <p className="text-xs text-muted-foreground">{category.count} files</p>
                  </CardContent>
                </Card>
              ))}
            </div>

            {/* Documents Grid/List */}
            {viewMode === 'grid' ? (
              <div className="grid md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                {filteredDocuments.map((document) => (
                  <Card key={document.id} className="hover:shadow-md transition-shadow">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-3">
                        {getFileIcon(document.type)}
                        <Badge variant={getStatusBadgeVariant(document.status)} className="text-xs">
                          {document.status}
                        </Badge>
                      </div>
                      <h3 className="font-medium text-sm mb-1 truncate" title={document.name}>
                        {document.name}
                      </h3>
                      <p className="text-xs text-muted-foreground mb-2">
                        {formatFileSize(document.size)} • {new Date(document.uploadedAt).toLocaleDateString()}
                      </p>
                      <div className="flex flex-wrap gap-1 mb-3">
                        {document.tags.slice(0, 2).map((tag) => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                        {document.tags.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{document.tags.length - 2}
                          </Badge>
                        )}
                      </div>
                      <div className="flex space-x-1">
                        <Button size="sm" variant="outline" className="flex-1">
                          <Eye className="w-3 h-3 mr-1" />
                          View
                        </Button>
                        <Button size="sm" variant="outline" className="flex-1">
                          <Download className="w-3 h-3 mr-1" />
                          Download
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDelete(document.id)}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : (
              <Card>
                <CardContent className="p-0">
                  <div className="divide-y">
                    {filteredDocuments.map((document) => (
                      <div key={document.id} className="p-4 flex items-center justify-between hover:bg-muted/50">
                        <div className="flex items-center space-x-4">
                          {getFileIcon(document.type)}
                          <div>
                            <h3 className="font-medium">{document.name}</h3>
                            <p className="text-sm text-muted-foreground">
                              {formatFileSize(document.size)} • Uploaded {new Date(document.uploadedAt).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={getStatusBadgeVariant(document.status)}>
                            {document.status}
                          </Badge>
                          <div className="flex space-x-1">
                            <Button size="sm" variant="outline">
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button size="sm" variant="outline">
                              <Download className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleDelete(document.id)}
                              className="text-red-600 hover:text-red-700"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {filteredDocuments.length === 0 && (
              <div className="text-center py-12">
                <FileText className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No documents found</h3>
                <p className="text-muted-foreground mb-4">
                  {searchQuery || selectedCategory !== 'all' || selectedType !== 'all'
                    ? 'Try adjusting your search or filters'
                    : 'Upload your first document to get started'
                  }
                </p>
                <Button onClick={() => setShowUploadDialog(true)}>
                  <Upload className="w-4 h-4 mr-2" />
                  Upload Document
                </Button>
              </div>
            )}
        </div>
      </div>
    )
  }