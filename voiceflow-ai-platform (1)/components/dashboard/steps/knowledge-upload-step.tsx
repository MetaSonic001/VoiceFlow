"use client"

import React, { useState } from 'react'
import { Upload, FileText, Link, Database, Plus, X } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface KnowledgeUploadStepProps {
  data: Record<string, any>
  initialData?: Record<string, any>
  onDataChange: (data: Record<string, any>) => void
  onNext: () => void
  onPrevious: () => void
  canGoNext: boolean
  canGoPrevious: boolean
}

export function KnowledgeUploadStep({ data, onDataChange, initialData }: KnowledgeUploadStepProps) {
  const [uploadedFiles, setUploadedFiles] = useState<string[]>(initialData?.uploadedFiles ?? data.uploadedFiles ?? [])
  const [websiteUrls, setWebsiteUrls] = useState<string[]>(initialData?.websiteUrls ?? data.websiteUrls ?? [''])
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true)
    } else if (e.type === "dragleave") {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const files = Array.from(e.dataTransfer.files).map(file => file.name)
      const newFiles = [...uploadedFiles, ...files]
      setUploadedFiles(newFiles)
      updateData({ uploadedFiles: newFiles })
    }
  }

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const files = Array.from(e.target.files).map(file => file.name)
      const newFiles = [...uploadedFiles, ...files]
      setUploadedFiles(newFiles)
      updateData({ uploadedFiles: newFiles })
    }
  }

  const addWebsiteUrl = () => {
    const newUrls = [...websiteUrls, '']
    setWebsiteUrls(newUrls)
    updateData({ websiteUrls: newUrls })
  }

  const updateWebsiteUrl = (index: number, url: string) => {
    const newUrls = [...websiteUrls]
    newUrls[index] = url
    setWebsiteUrls(newUrls)
    updateData({ websiteUrls: newUrls })
  }

  const removeWebsiteUrl = (index: number) => {
    const newUrls = websiteUrls.filter((_, i) => i !== index)
    setWebsiteUrls(newUrls)
    updateData({ websiteUrls: newUrls })
  }

  const removeFile = (index: number) => {
    const newFiles = uploadedFiles.filter((_, i) => i !== index)
    setUploadedFiles(newFiles)
    updateData({ uploadedFiles: newFiles })
  }

  const updateData = (newData: Record<string, any>) => {
    const merged = { ...data, ...initialData, uploadedFiles, websiteUrls, ...newData }
    onDataChange(merged)
  }

  return (
    <div className="w-full max-w-4xl mx-auto">
      <div className="space-y-8">
        {/* Header */}
        <div className="text-center space-y-3">
          <h2 className="text-2xl sm:text-3xl font-bold tracking-tight">Upload Knowledge Base</h2>
          <p className="text-base text-muted-foreground max-w-2xl mx-auto">
            Add documents and websites to train your agent
          </p>
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* File Upload Card */}
          <Card className="shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileText className="h-5 w-5 text-primary" />
                <span>Upload Documents</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-all duration-200 cursor-pointer ${dragActive
                    ? 'border-primary bg-primary/10 scale-[0.98]'
                    : 'border-muted-foreground/25 hover:border-primary/50 hover:bg-accent/5'
                  }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
              >
                <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
                <p className="text-sm text-muted-foreground mb-3">
                  Drag and drop files here, or click to select
                </p>
                <p className="text-xs text-muted-foreground mb-4">
                  Supported: PDF, DOC, DOCX, TXT, MD
                </p>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.md"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <Label htmlFor="file-upload">
                  <Button variant="outline" size="lg" className="cursor-pointer">
                    <Upload className="h-4 w-4 mr-2" />
                    Choose Files
                  </Button>
                </Label>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="space-y-3">
                  <Label className="text-sm font-medium">Uploaded Files ({uploadedFiles.length})</Label>
                  <div className="space-y-2 max-h-40 overflow-y-auto pr-2">
                    {uploadedFiles.map((file, index) => (
                      <div
                        key={index}
                        className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
                      >
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          <FileText className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          <span className="truncate text-sm">{file}</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => removeFile(index)}
                          className="flex-shrink-0 h-8 w-8 p-0"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Website URLs Card */}
          <Card className="shadow-sm">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center gap-2 text-lg">
                <Link className="h-5 w-5 text-primary" />
                <span>Website URLs</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Add website URLs to crawl and extract knowledge from
              </p>

              <div className="space-y-3 max-h-[280px] overflow-y-auto pr-2">
                {websiteUrls.map((url, index) => (
                  <div key={index} className="flex gap-2">
                    <div className="relative flex-1">
                      <Link className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                      <Input
                        type="url"
                        placeholder="https://example.com"
                        value={url}
                        onChange={(e) => updateWebsiteUrl(index, e.target.value)}
                        className="pl-10 h-11"
                      />
                    </div>
                    {websiteUrls.length > 1 && (
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => removeWebsiteUrl(index)}
                        className="flex-shrink-0 h-11 w-11"
                      >
                        <X className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>

              <Button
                variant="outline"
                onClick={addWebsiteUrl}
                className="w-full h-11"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Another URL
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Knowledge Base Summary */}
        <Card className="bg-primary/5 border-primary/20 shadow-sm">
          <CardHeader className="pb-4">
            <CardTitle className="flex items-center gap-2 text-lg text-primary">
              <Database className="h-5 w-5" />
              <span>Knowledge Base Summary</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6 text-center">
              <div className="space-y-2">
                <div className="text-3xl font-bold text-primary">{uploadedFiles.length}</div>
                <div className="text-sm text-muted-foreground">Documents Uploaded</div>
              </div>
              <div className="space-y-2">
                <div className="text-3xl font-bold text-primary">
                  {websiteUrls.filter(url => url.trim()).length}
                </div>
                <div className="text-sm text-muted-foreground">Website URLs Added</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

