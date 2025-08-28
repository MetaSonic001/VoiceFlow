"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, FileText, Link, Plus, X } from "lucide-react"

interface KnowledgeUploadProps {
  onComplete: (data: any) => void
}

export function KnowledgeUpload({ onComplete }: KnowledgeUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  const [websites, setWebsites] = useState<string[]>([])
  const [newWebsite, setNewWebsite] = useState("")
  const [faqText, setFaqText] = useState("")

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    setUploadedFiles([...uploadedFiles, ...files])
  }

  const removeFile = (index: number) => {
    setUploadedFiles(uploadedFiles.filter((_, i) => i !== index))
  }

  const addWebsite = () => {
    if (newWebsite && !websites.includes(newWebsite)) {
      setWebsites([...websites, newWebsite])
      setNewWebsite("")
    }
  }

  const removeWebsite = (index: number) => {
    setWebsites(websites.filter((_, i) => i !== index))
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onComplete({
      knowledge: {
        files: uploadedFiles,
        websites,
        faqText,
      },
    })
  }

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Upload className="w-12 h-12 text-accent mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Upload your knowledge base</h2>
        <p className="text-muted-foreground">
          Provide documents, FAQs, and website content so your agent can answer questions accurately.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* File Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Documents & Files</span>
            </CardTitle>
            <CardDescription>Upload PDFs, Word docs, text files, or other documents</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="border-2 border-dashed border-border rounded-lg p-6 text-center">
              <Input
                type="file"
                multiple
                accept=".pdf,.doc,.docx,.txt,.md"
                onChange={handleFileUpload}
                className="hidden"
                id="file-upload"
              />
              <Label htmlFor="file-upload" className="cursor-pointer">
                <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  Click to upload files or drag and drop
                  <br />
                  PDF, DOC, TXT, MD files supported
                </p>
              </Label>
            </div>

            {uploadedFiles.length > 0 && (
              <div className="space-y-2">
                <Label>Uploaded Files</Label>
                {uploadedFiles.map((file, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-muted rounded">
                    <span className="text-sm">{file.name}</span>
                    <Button variant="ghost" size="sm" onClick={() => removeFile(index)}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Website URLs */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Link className="w-5 h-5" />
              <span>Website Content</span>
            </CardTitle>
            <CardDescription>Add website URLs to crawl for content</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex space-x-2">
              <Input
                placeholder="https://yourwebsite.com/help"
                value={newWebsite}
                onChange={(e) => setNewWebsite(e.target.value)}
              />
              <Button type="button" onClick={addWebsite} disabled={!newWebsite}>
                <Plus className="w-4 h-4" />
              </Button>
            </div>

            {websites.length > 0 && (
              <div className="space-y-2">
                <Label>Added Websites</Label>
                {websites.map((website, index) => (
                  <div key={index} className="flex items-center justify-between p-2 bg-muted rounded">
                    <span className="text-sm">{website}</span>
                    <Button variant="ghost" size="sm" onClick={() => removeWebsite(index)}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* FAQ Text */}
        <Card>
          <CardHeader>
            <CardTitle>Frequently Asked Questions</CardTitle>
            <CardDescription>Paste your FAQs or common questions and answers</CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              placeholder="Q: What are your business hours?
A: We're open Monday-Friday 9AM-5PM EST.

Q: How do I return a product?
A: You can return products within 30 days..."
              value={faqText}
              onChange={(e) => setFaqText(e.target.value)}
              rows={8}
            />
          </CardContent>
        </Card>

        <Button
          type="submit"
          className="w-full"
          disabled={uploadedFiles.length === 0 && websites.length === 0 && !faqText}
        >
          Continue to Voice Setup
        </Button>
      </form>
    </div>
  )
}
