"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import DatePickerWithRange from "@/components/ui/date-range-picker"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import {
  Download,
  FileText,
  FileSpreadsheet,
  FileJson,
  Calendar,
  Filter,
  BarChart3,
  TrendingUp,
  Users,
  MessageSquare,
  Phone,
  Clock
} from "lucide-react"
import { apiClient } from "@/lib/api-client"
import { DateRange } from "react-day-picker"

interface ReportTemplate {
  id: string
  name: string
  description: string
  type: 'analytics' | 'usage' | 'performance' | 'financial'
  format: 'csv' | 'xlsx' | 'json' | 'pdf'
  fields: string[]
  lastGenerated?: string
}

interface ExportJob {
  id: string
  templateId: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  createdAt: string
  completedAt?: string
  downloadUrl?: string
  error?: string
}

export default function ReportsPage() {
  const [templates, setTemplates] = useState<ReportTemplate[]>([])
  const [exportJobs, setExportJobs] = useState<ExportJob[]>([])
  const [selectedTemplate, setSelectedTemplate] = useState<string>('')
  const [selectedFormat, setSelectedFormat] = useState<string>('csv')
  const [dateRange, setDateRange] = useState<DateRange | undefined>()
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    loadReportTemplates()
    loadExportJobs()
  }, [])

  const loadReportTemplates = async () => {
    try {
      // This would call a reports API endpoint
      // const data = await apiClient.getReportTemplates()
      // For now, using mock data
      const mockTemplates: ReportTemplate[] = [
        {
          id: 'user-activity',
          name: 'User Activity Report',
          description: 'Detailed user interactions, login patterns, and engagement metrics',
          type: 'analytics',
          format: 'xlsx',
          fields: ['user_id', 'login_count', 'session_duration', 'features_used', 'last_active'],
          lastGenerated: '2024-01-15T10:30:00Z'
        },
        {
          id: 'conversation-analytics',
          name: 'Conversation Analytics',
          description: 'Chat conversations, response times, and satisfaction scores',
          type: 'usage',
          format: 'csv',
          fields: ['conversation_id', 'user_id', 'start_time', 'duration', 'messages_count', 'satisfaction_score'],
          lastGenerated: '2024-01-15T09:15:00Z'
        },
        {
          id: 'system-performance',
          name: 'System Performance Report',
          description: 'Server metrics, API response times, and error rates',
          type: 'performance',
          format: 'json',
          fields: ['timestamp', 'cpu_usage', 'memory_usage', 'response_time', 'error_count', 'uptime'],
          lastGenerated: '2024-01-15T08:45:00Z'
        },
        {
          id: 'billing-summary',
          name: 'Billing Summary',
          description: 'Usage costs, API calls, and billing breakdown',
          type: 'financial',
          format: 'pdf',
          fields: ['period', 'api_calls', 'storage_used', 'cost_breakdown', 'total_amount'],
          lastGenerated: '2024-01-14T23:00:00Z'
        },
        {
          id: 'agent-performance',
          name: 'Agent Performance Report',
          description: 'Agent response accuracy, processing times, and success rates',
          type: 'analytics',
          format: 'xlsx',
          fields: ['agent_id', 'queries_handled', 'accuracy_score', 'avg_response_time', 'user_satisfaction'],
          lastGenerated: '2024-01-15T11:00:00Z'
        }
      ]
      setTemplates(mockTemplates)
    } catch (error) {
      console.error('Failed to load report templates:', error)
    }
  }

  const loadExportJobs = async () => {
    try {
      // This would call an export jobs API endpoint
      // const data = await apiClient.getExportJobs()
      // For now, using mock data
      const mockJobs: ExportJob[] = [
        {
          id: 'exp-001',
          templateId: 'user-activity',
          status: 'completed',
          createdAt: '2024-01-15T10:00:00Z',
          completedAt: '2024-01-15T10:05:00Z',
          downloadUrl: '/downloads/user-activity-2024-01-15.xlsx'
        },
        {
          id: 'exp-002',
          templateId: 'conversation-analytics',
          status: 'processing',
          createdAt: '2024-01-15T11:00:00Z'
        },
        {
          id: 'exp-003',
          templateId: 'system-performance',
          status: 'failed',
          createdAt: '2024-01-15T09:00:00Z',
          error: 'Database connection timeout'
        }
      ]
      setExportJobs(mockJobs)
    } catch (error) {
      console.error('Failed to load export jobs:', error)
    }
  }

  const handleExport = async () => {
    if (!selectedTemplate) return

    setLoading(true)
    try {
      // This would call an export API endpoint
      // const job = await apiClient.createExportJob({
      //   templateId: selectedTemplate,
      //   format: selectedFormat,
      //   dateRange: dateRange
      // })

      // Mock creating a new export job
      const newJob: ExportJob = {
        id: `exp-${Date.now()}`,
        templateId: selectedTemplate,
        status: 'pending',
        createdAt: new Date().toISOString()
      }

      setExportJobs(prev => [newJob, ...prev])

      // Simulate processing
      setTimeout(() => {
        setExportJobs(prev =>
          prev.map(job =>
            job.id === newJob.id
              ? { ...job, status: 'processing' as const }
              : job
          )
        )

        setTimeout(() => {
          setExportJobs(prev =>
            prev.map(job =>
              job.id === newJob.id
                ? {
                    ...job,
                    status: 'completed' as const,
                    completedAt: new Date().toISOString(),
                    downloadUrl: `/downloads/${selectedTemplate}-${new Date().toISOString().split('T')[0]}.${selectedFormat}`
                  }
                : job
            )
          )
        }, 3000)
      }, 1000)

    } catch (error) {
      console.error('Failed to create export job:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'default'
      case 'processing': return 'secondary'
      case 'pending': return 'outline'
      case 'failed': return 'destructive'
      default: return 'outline'
    }
  }

  const getFormatIcon = (format: string) => {
    switch (format) {
      case 'csv': return <FileSpreadsheet className="w-4 h-4" />
      case 'xlsx': return <FileSpreadsheet className="w-4 h-4" />
      case 'json': return <FileJson className="w-4 h-4" />
      case 'pdf': return <FileText className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'analytics': return <BarChart3 className="w-4 h-4" />
      case 'usage': return <TrendingUp className="w-4 h-4" />
      case 'performance': return <Clock className="w-4 h-4" />
      case 'financial': return <FileText className="w-4 h-4" />
      default: return <FileText className="w-4 h-4" />
    }
  }

  const selectedTemplateData = templates.find(t => t.id === selectedTemplate)

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Reports & Export</h1>
                <p className="text-muted-foreground">Generate and download detailed reports</p>
              </div>
            </div>

            {/* Export Configuration */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Generate New Report</CardTitle>
                <CardDescription>Select a report template and export options</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Report Template</label>
                    <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
                      <SelectTrigger>
                        <SelectValue placeholder="Select a report template" />
                      </SelectTrigger>
                      <SelectContent>
                        {templates.map((template) => (
                          <SelectItem key={template.id} value={template.id}>
                            <div className="flex items-center space-x-2">
                              {getTypeIcon(template.type)}
                              <span>{template.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium">Export Format</label>
                    <Select value={selectedFormat} onValueChange={setSelectedFormat}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="csv">
                          <div className="flex items-center space-x-2">
                            <FileSpreadsheet className="w-4 h-4" />
                            <span>CSV</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="xlsx">
                          <div className="flex items-center space-x-2">
                            <FileSpreadsheet className="w-4 h-4" />
                            <span>Excel (XLSX)</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="json">
                          <div className="flex items-center space-x-2">
                            <FileJson className="w-4 h-4" />
                            <span>JSON</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="pdf">
                          <div className="flex items-center space-x-2">
                            <FileText className="w-4 h-4" />
                            <span>PDF</span>
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Date Range (Optional)</label>
                  <DatePickerWithRange
                    date={dateRange}
                    onDateChange={setDateRange}
                  />
                </div>

                {selectedTemplateData && (
                  <div className="p-4 bg-muted rounded-lg">
                    <h4 className="font-medium mb-2">{selectedTemplateData.name}</h4>
                    <p className="text-sm text-muted-foreground mb-2">{selectedTemplateData.description}</p>
                    <div className="flex flex-wrap gap-1">
                      {selectedTemplateData.fields.map((field) => (
                        <Badge key={field} variant="outline" className="text-xs">
                          {field}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                <Button
                  onClick={handleExport}
                  disabled={!selectedTemplate || loading}
                  className="w-full md:w-auto"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Generating Report...
                    </>
                  ) : (
                    <>
                      <Download className="w-4 h-4 mr-2" />
                      Generate Report
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Report Templates */}
            <Card className="mb-6">
              <CardHeader>
                <CardTitle>Report Templates</CardTitle>
                <CardDescription>Available report templates and their descriptions</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {templates.map((template) => (
                    <div key={template.id} className="p-4 border rounded-lg hover:bg-muted/50 cursor-pointer transition-colors">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          {getTypeIcon(template.type)}
                          <h4 className="font-medium">{template.name}</h4>
                        </div>
                        <Badge variant="outline">{template.format.toUpperCase()}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mb-3">{template.description}</p>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{template.fields.length} fields</span>
                        {template.lastGenerated && (
                          <span>Last: {new Date(template.lastGenerated).toLocaleDateString()}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Export History */}
            <Card>
              <CardHeader>
                <CardTitle>Export History</CardTitle>
                <CardDescription>Recent report exports and their status</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {exportJobs.map((job) => {
                    const template = templates.find(t => t.id === job.templateId)
                    return (
                      <div key={job.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center space-x-4">
                          {getFormatIcon(selectedFormat)}
                          <div>
                            <p className="font-medium">{template?.name}</p>
                            <p className="text-sm text-muted-foreground">
                              Created: {new Date(job.createdAt).toLocaleString()}
                              {job.completedAt && ` • Completed: ${new Date(job.completedAt).toLocaleString()}`}
                            </p>
                            {job.error && (
                              <p className="text-sm text-red-600 mt-1">{job.error}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={getStatusBadgeVariant(job.status)}>
                            {job.status}
                          </Badge>
                          {job.downloadUrl && job.status === 'completed' && (
                            <Button size="sm" variant="outline">
                              <Download className="w-4 h-4 mr-1" />
                              Download
                            </Button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}