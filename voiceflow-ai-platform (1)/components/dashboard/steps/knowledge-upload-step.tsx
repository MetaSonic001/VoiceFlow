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
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-xl sm:text-2xl font-bold">Upload Knowledge Base</h2>
        <p className="text-sm sm:text-base text-muted-foreground">Add documents and websites to train your agent</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
        {/* File Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
              <FileText className="h-4 w-4 sm:h-5 sm:w-5" />
              <span>Upload Documents</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div
              className={`border-2 border-dashed rounded-lg p-4 sm:p-6 text-center transition-colors ${
                dragActive ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'
              }`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
            >
              <Upload className="h-8 w-8 sm:h-10 sm:w-10 mx-auto mb-3 sm:mb-4 text-muted-foreground" />
              <p className="text-xs sm:text-sm text-muted-foreground mb-2">
                Drag and drop files here, or click to select
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
                <Button variant="outline" className="cursor-pointer text-xs sm:text-sm">
                  Choose Files
                </Button>
              </Label>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="space-y-2">
                <Label className="text-sm">Uploaded Files:</Label>
                <div className="space-y-2 max-h-32 overflow-y-auto">
                  {uploadedFiles.map((file, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-muted rounded text-sm">
                      <span className="truncate mr-2">{file}</span>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeFile(index)}
                        className="flex-shrink-0"
                      >
                        <X className="h-3 w-3 sm:h-4 sm:w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Website URLs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
              <Link className="h-4 w-4 sm:h-5 sm:w-5" />
              <span>Website URLs</span>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs sm:text-sm text-muted-foreground">
              Add website URLs to crawl and extract knowledge from
            </p>
            
            <div className="space-y-3">
              {websiteUrls.map((url, index) => (
                <div key={index} className="flex space-x-2">
                  <Input
                    type="url"
                    placeholder="https://example.com"
                    value={url}
                    onChange={(e) => updateWebsiteUrl(index, e.target.value)}
                    className="text-sm"
                  />
                  {websiteUrls.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeWebsiteUrl(index)}
                      className="flex-shrink-0"
                    >
                      <X className="h-3 w-3 sm:h-4 sm:w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            
            <Button
              variant="outline"
              onClick={addWebsiteUrl}
              className="w-full text-sm"
            >
              <Plus className="h-3 w-3 sm:h-4 sm:w-4 mr-2" />
              Add Another URL
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Knowledge Base Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2 text-base sm:text-lg">
            <Database className="h-4 w-4 sm:h-5 sm:w-5" />
            <span>Knowledge Base Summary</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-center">
            <div>
              <div className="text-xl sm:text-2xl font-bold text-primary">{uploadedFiles.length}</div>
              <div className="text-xs sm:text-sm text-muted-foreground">Documents</div>
            </div>
            <div>
              <div className="text-xl sm:text-2xl font-bold text-primary">
                {websiteUrls.filter(url => url.trim()).length}
              </div>
              <div className="text-xs sm:text-sm text-muted-foreground">Website URLs</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}