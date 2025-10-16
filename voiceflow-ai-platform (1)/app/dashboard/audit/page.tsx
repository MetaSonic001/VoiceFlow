"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import {
  Search,
  Filter,
  Download,
  Eye,
  User,
  Settings,
  FileText,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Calendar,
  Plus,
  Trash2,
  Activity
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface AuditLog {
  id: string
  timestamp: string
  userId: string
  userName: string
  action: string
  resource: string
  resourceId?: string
  details: string
  ipAddress: string
  userAgent: string
  status: 'success' | 'failure' | 'warning'
  severity: 'low' | 'medium' | 'high' | 'critical'
}

export default function AuditLogsPage() {
  const [logs, setLogs] = useState<AuditLog[]>([])
  const [filteredLogs, setFilteredLogs] = useState<AuditLog[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedAction, setSelectedAction] = useState<string>('all')
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all')
  const [selectedUser, setSelectedUser] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null)

  const logsPerPage = 20

  useEffect(() => {
    loadAuditLogs()
  }, [])

  useEffect(() => {
    filterLogs()
  }, [logs, searchQuery, selectedAction, selectedSeverity, selectedUser])

  const loadAuditLogs = async () => {
    try {
      setLoading(true)
      // This would call an audit logs API endpoint
      // const data = await apiClient.getAuditLogs()
      // For now, using mock data
      const mockLogs: AuditLog[] = [
        {
          id: 'log-001',
          timestamp: '2024-01-15T14:30:00Z',
          userId: 'user-123',
          userName: 'John Doe',
          action: 'CREATE_AGENT',
          resource: 'Agent',
          resourceId: 'agent-456',
          details: 'Created new agent "Customer Support Bot"',
          ipAddress: '192.168.1.100',
          userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          status: 'success',
          severity: 'medium'
        },
        {
          id: 'log-002',
          timestamp: '2024-01-15T14:25:00Z',
          userId: 'user-123',
          userName: 'John Doe',
          action: 'LOGIN',
          resource: 'Authentication',
          details: 'User logged in successfully',
          ipAddress: '192.168.1.100',
          userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          status: 'success',
          severity: 'low'
        },
        {
          id: 'log-003',
          timestamp: '2024-01-15T14:20:00Z',
          userId: 'user-456',
          userName: 'Jane Smith',
          action: 'DELETE_DOCUMENT',
          resource: 'Document',
          resourceId: 'doc-789',
          details: 'Deleted document "User Manual.pdf"',
          ipAddress: '192.168.1.101',
          userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
          status: 'success',
          severity: 'high'
        },
        {
          id: 'log-004',
          timestamp: '2024-01-15T14:15:00Z',
          userId: 'system',
          userName: 'System',
          action: 'BACKUP_COMPLETED',
          resource: 'System',
          details: 'Daily backup completed successfully',
          ipAddress: '127.0.0.1',
          userAgent: 'System Service',
          status: 'success',
          severity: 'low'
        },
        {
          id: 'log-005',
          timestamp: '2024-01-15T14:10:00Z',
          userId: 'user-789',
          userName: 'Bob Wilson',
          action: 'FAILED_LOGIN',
          resource: 'Authentication',
          details: 'Failed login attempt - invalid password',
          ipAddress: '10.0.0.50',
          userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
          status: 'failure',
          severity: 'high'
        },
        {
          id: 'log-006',
          timestamp: '2024-01-15T14:05:00Z',
          userId: 'user-123',
          userName: 'John Doe',
          action: 'UPDATE_SETTINGS',
          resource: 'Settings',
          details: 'Updated notification preferences',
          ipAddress: '192.168.1.100',
          userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
          status: 'success',
          severity: 'low'
        },
        {
          id: 'log-007',
          timestamp: '2024-01-15T14:00:00Z',
          userId: 'system',
          userName: 'System',
          action: 'SECURITY_ALERT',
          resource: 'Security',
          details: 'Multiple failed login attempts detected from IP 10.0.0.50',
          ipAddress: '127.0.0.1',
          userAgent: 'Security Monitor',
          status: 'warning',
          severity: 'critical'
        }
      ]
      setLogs(mockLogs)
    } catch (error) {
      console.error('Failed to load audit logs:', error)
    } finally {
      setLoading(false)
    }
  }

  const filterLogs = () => {
    let filtered = logs

    if (searchQuery) {
      filtered = filtered.filter(log =>
        log.userName.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
        log.resource.toLowerCase().includes(searchQuery.toLowerCase())
      )
    }

    if (selectedAction !== 'all') {
      filtered = filtered.filter(log => log.action === selectedAction)
    }

    if (selectedSeverity !== 'all') {
      filtered = filtered.filter(log => log.severity === selectedSeverity)
    }

    if (selectedUser !== 'all') {
      filtered = filtered.filter(log => log.userId === selectedUser)
    }

    setFilteredLogs(filtered)
    setCurrentPage(1)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'failure': return <XCircle className="w-4 h-4 text-red-500" />
      case 'warning': return <AlertTriangle className="w-4 h-4 text-yellow-500" />
      default: return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getSeverityBadgeVariant = (severity: string) => {
    switch (severity) {
      case 'low': return 'secondary'
      case 'medium': return 'default'
      case 'high': return 'destructive'
      case 'critical': return 'destructive'
      default: return 'outline'
    }
  }

  const getActionIcon = (action: string) => {
    if (action.includes('CREATE') || action.includes('ADD')) return <Plus className="w-4 h-4" />
    if (action.includes('UPDATE') || action.includes('EDIT')) return <Settings className="w-4 h-4" />
    if (action.includes('DELETE') || action.includes('REMOVE')) return <Trash2 className="w-4 h-4" />
    if (action.includes('LOGIN')) return <User className="w-4 h-4" />
    if (action.includes('DOCUMENT')) return <FileText className="w-4 h-4" />
    if (action.includes('SECURITY')) return <Shield className="w-4 h-4" />
    return <Activity className="w-4 h-4" />
  }

  const paginatedLogs = filteredLogs.slice(
    (currentPage - 1) * logsPerPage,
    currentPage * logsPerPage
  )

  const totalPages = Math.ceil(filteredLogs.length / logsPerPage)

  const exportLogs = () => {
    // This would export the filtered logs to CSV/JSON
    console.log('Exporting logs:', filteredLogs)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="flex">
          <DashboardSidebar />
          <div className="flex-1 ml-64">
            <div className="p-6">
              <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
                <span className="ml-2">Loading audit logs...</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <DashboardSidebar />
        <div className="flex-1 ml-64">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h1 className="text-3xl font-bold">Audit Logs</h1>
                <p className="text-muted-foreground">Track all user actions and system events</p>
              </div>
              <Button onClick={exportLogs}>
                <Download className="w-4 h-4 mr-2" />
                Export Logs
              </Button>
            </div>

            {/* Filters */}
            <Card className="mb-6">
              <CardContent className="pt-6">
                <div className="grid md:grid-cols-2 lg:grid-cols-5 gap-4">
                  <div className="lg:col-span-2">
                    <div className="relative">
                      <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search logs..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="pl-10"
                      />
                    </div>
                  </div>
                  <Select value={selectedAction} onValueChange={setSelectedAction}>
                    <SelectTrigger>
                      <SelectValue placeholder="Action" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Actions</SelectItem>
                      <SelectItem value="CREATE_AGENT">Create Agent</SelectItem>
                      <SelectItem value="UPDATE_AGENT">Update Agent</SelectItem>
                      <SelectItem value="DELETE_AGENT">Delete Agent</SelectItem>
                      <SelectItem value="LOGIN">Login</SelectItem>
                      <SelectItem value="LOGOUT">Logout</SelectItem>
                      <SelectItem value="UPLOAD_DOCUMENT">Upload Document</SelectItem>
                      <SelectItem value="DELETE_DOCUMENT">Delete Document</SelectItem>
                      <SelectItem value="UPDATE_SETTINGS">Update Settings</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
                    <SelectTrigger>
                      <SelectValue placeholder="Severity" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Severities</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select value={selectedUser} onValueChange={setSelectedUser}>
                    <SelectTrigger>
                      <SelectValue placeholder="User" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Users</SelectItem>
                      <SelectItem value="user-123">John Doe</SelectItem>
                      <SelectItem value="user-456">Jane Smith</SelectItem>
                      <SelectItem value="user-789">Bob Wilson</SelectItem>
                      <SelectItem value="system">System</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </CardContent>
            </Card>

            {/* Logs Table */}
            <Card>
              <CardHeader>
                <CardTitle>Activity Logs</CardTitle>
                <CardDescription>
                  Showing {paginatedLogs.length} of {filteredLogs.length} logs
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Timestamp</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Resource</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Details</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {paginatedLogs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell>
                          <div className="text-sm">
                            {new Date(log.timestamp).toLocaleString()}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="font-medium">{log.userName}</div>
                          <div className="text-xs text-muted-foreground">{log.ipAddress}</div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            {getActionIcon(log.action)}
                            <span className="text-sm">{log.action.replace('_', ' ')}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">{log.resource}</div>
                          {log.resourceId && (
                            <div className="text-xs text-muted-foreground">{log.resourceId}</div>
                          )}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-1">
                            {getStatusIcon(log.status)}
                            <span className="text-sm capitalize">{log.status}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={getSeverityBadgeVariant(log.severity)}>
                            {log.severity}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm max-w-xs truncate" title={log.details}>
                            {log.details}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setSelectedLog(log)}
                          >
                            <Eye className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm text-muted-foreground">
                      Page {currentPage} of {totalPages}
                    </div>
                    <div className="flex space-x-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                      >
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                      >
                        Next
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Log Details Modal */}
            {selectedLog && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold">Log Details</h3>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setSelectedLog(null)}
                    >
                      ×
                    </Button>
                  </div>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="text-sm font-medium">Timestamp</label>
                        <div className="text-sm">{new Date(selectedLog.timestamp).toLocaleString()}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">User</label>
                        <div className="text-sm">{selectedLog.userName}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">Action</label>
                        <div className="text-sm">{selectedLog.action}</div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">Status</label>
                        <div className="flex items-center space-x-1">
                          {getStatusIcon(selectedLog.status)}
                          <span className="text-sm capitalize">{selectedLog.status}</span>
                        </div>
                      </div>
                      <div>
                        <label className="text-sm font-medium">Severity</label>
                        <Badge variant={getSeverityBadgeVariant(selectedLog.severity)}>
                          {selectedLog.severity}
                        </Badge>
                      </div>
                      <div>
                        <label className="text-sm font-medium">IP Address</label>
                        <div className="text-sm">{selectedLog.ipAddress}</div>
                      </div>
                    </div>

                    <div>
                      <label className="text-sm font-medium">Details</label>
                      <div className="text-sm bg-gray-50 p-3 rounded mt-1">{selectedLog.details}</div>
                    </div>

                    <div>
                      <label className="text-sm font-medium">User Agent</label>
                      <div className="text-xs bg-gray-50 p-3 rounded mt-1 font-mono">{selectedLog.userAgent}</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}