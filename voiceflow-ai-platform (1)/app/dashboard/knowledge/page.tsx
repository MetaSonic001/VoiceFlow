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
  Plus,
  Edit,
  Trash2,
  Download,
  Eye,
  Filter,
  Grid,
  List,
  Folder,
  Tag
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

  useEffect(() => {
    loadDocuments()
    loadCategories()
  }, [])

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