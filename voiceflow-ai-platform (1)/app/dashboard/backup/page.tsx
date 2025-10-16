"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Progress } from "@/components/ui/progress"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import {
  Download,
  Upload,
  Database,
  HardDrive,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw,
  Archive,
  FileText,
  Settings,
  Calendar,
  Zap
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Backup {
  id: string
  name: string
  type: 'full' | 'incremental' | 'configuration'
  status: 'completed' | 'in_progress' | 'failed' | 'scheduled'
  size: number
  createdAt: string
  completedAt?: string
  scheduledFor?: string
  includes: string[]
  downloadUrl?: string
  error?: string
}

interface BackupSchedule {
  id: string
  name: string
  type: 'full' | 'incremental'
  frequency: 'daily' | 'weekly' | 'monthly'
  time: string
  enabled: boolean
  lastRun?: string
  nextRun: string
}

export default function BackupRestorePage() {
  const [backups, setBackups] = useState<Backup[]>([])
  const [schedules, setSchedules] = useState<BackupSchedule[]>([])
  const [currentOperation, setCurrentOperation] = useState<{
    type: 'backup' | 'restore'
    progress: number
    status: string
  } | null>(null)
  const [showCreateBackup, setShowCreateBackup] = useState(false)
  const [showRestoreDialog, setShowRestoreDialog] = useState(false)
  const [selectedBackup, setSelectedBackup] = useState<Backup | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadBackups()
    loadSchedules()
  }, [])

  const loadBackups = async () => {
    try {
      setLoading(true)
      // This would call a backups API endpoint
      // const data = await apiClient.getBackups()
      // For now, using mock data
      const mockBackups: Backup[] = [
        {
          id: 'backup-001',
          name: 'Daily Full Backup - 2024-01-15',
          type: 'full',
          status: 'completed',
          size: 1073741824, // 1GB
          createdAt: '2024-01-15T02:00:00Z',
          completedAt: '2024-01-15T02:30:00Z',
          includes: ['database', 'documents', 'configurations', 'user_data'],
          downloadUrl: '/downloads/backup-2024-01-15.zip'
        },
        {
          id: 'backup-002',
          name: 'Incremental Backup - 2024-01-14',
          type: 'incremental',
          status: 'completed',
          size: 524288000, // 500MB
          createdAt: '2024-01-14T14:00:00Z',
          completedAt: '2024-01-14T14:15:00Z',
          includes: ['database_changes', 'new_documents'],
          downloadUrl: '/downloads/backup-2024-01-14.zip'
        },
        {
          id: 'backup-003',
          name: 'Configuration Backup - 2024-01-13',
          type: 'configuration',
          status: 'completed',
          size: 10485760, // 10MB
          createdAt: '2024-01-13T10:00:00Z',
          completedAt: '2024-01-13T10:02:00Z',
          includes: ['agent_configs', 'system_settings', 'api_keys'],
          downloadUrl: '/downloads/config-backup-2024-01-13.zip'
        },
        {
          id: 'backup-004',
          name: 'Scheduled Full Backup',
          type: 'full',
          status: 'scheduled',
          size: 0,
          createdAt: '2024-01-15T12:00:00Z',
          scheduledFor: '2024-01-16T02:00:00Z',
          includes: ['database', 'documents', 'configurations', 'user_data']
        }
      ]
      setBackups(mockBackups)
    } catch (error) {
      console.error('Failed to load backups:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSchedules = async () => {
    try {
      // This would call a backup schedules API endpoint
      // const data = await apiClient.getBackupSchedules()
      // For now, using mock data
      const mockSchedules: BackupSchedule[] = [
        {
          id: 'schedule-001',
          name: 'Daily Full Backup',
          type: 'full',
          frequency: 'daily',
          time: '02:00',
          enabled: true,
          lastRun: '2024-01-15T02:00:00Z',
          nextRun: '2024-01-16T02:00:00Z'
        },
        {
          id: 'schedule-002',
          name: 'Weekly Incremental',
          type: 'incremental',
          frequency: 'weekly',
          time: '14:00',
          enabled: true,
          lastRun: '2024-01-14T14:00:00Z',
          nextRun: '2024-01-21T14:00:00Z'
        },
        {
          id: 'schedule-003',
          name: 'Monthly Configuration',
          type: 'configuration',
          frequency: 'monthly',
          time: '10:00',
          enabled: false,
          nextRun: '2024-02-01T10:00:00Z'
        }
      ]
      setSchedules(mockSchedules)
    } catch (error) {
      console.error('Failed to load backup schedules:', error)
    }
  }

  const createBackup = async (type: 'full' | 'incremental' | 'configuration') => {
    try {
      setCurrentOperation({
        type: 'backup',
        progress: 0,
        status: 'Initializing backup...'
      })

      // Simulate backup progress
      const progressInterval = setInterval(() => {
        setCurrentOperation(prev => {
          if (!prev) return null
          const newProgress = Math.min(prev.progress + Math.random() * 15, 95)
          return {
            ...prev,
            progress: newProgress,
            status: newProgress < 30 ? 'Backing up database...' :
                   newProgress < 60 ? 'Backing up documents...' :
                   newProgress < 90 ? 'Backing up configurations...' :
                   'Finalizing backup...'
          }
        })
      }, 1000)

      // This would call a create backup API endpoint
      // const result = await apiClient.createBackup({ type })

      setTimeout(() => {
        clearInterval(progressInterval)
        setCurrentOperation({
          type: 'backup',
          progress: 100,
          status: 'Backup completed successfully!'
        })

        // Add new backup to list
        const newBackup: Backup = {
          id: `backup-${Date.now()}`,
          name: `${type.charAt(0).toUpperCase() + type.slice(1)} Backup - ${new Date().toISOString().split('T')[0]}`,
          type,
          status: 'completed',
          size: type === 'full' ? 1073741824 : type === 'incremental' ? 524288000 : 10485760,
          createdAt: new Date().toISOString(),
          completedAt: new Date().toISOString(),
          includes: type === 'full'
            ? ['database', 'documents', 'configurations', 'user_data']
            : type === 'incremental'
            ? ['database_changes', 'new_documents']
            : ['agent_configs', 'system_settings', 'api_keys'],
          downloadUrl: `/downloads/${type}-backup-${new Date().toISOString().split('T')[0]}.zip`
        }

        setBackups(prev => [newBackup, ...prev])
        setTimeout(() => setCurrentOperation(null), 2000)
      }, 8000)

      setShowCreateBackup(false)
    } catch (error) {
      console.error('Failed to create backup:', error)
      setCurrentOperation(null)
    }
  }

  const restoreBackup = async (backupId: string) => {
    try {
      setCurrentOperation({
        type: 'restore',
        progress: 0,
        status: 'Preparing restore...'
      })

      // Simulate restore progress
      const progressInterval = setInterval(() => {
        setCurrentOperation(prev => {
          if (!prev) return null
          const newProgress = Math.min(prev.progress + Math.random() * 10, 95)
          return {
            ...prev,
            progress: newProgress,
            status: newProgress < 25 ? 'Restoring database...' :
                   newProgress < 50 ? 'Restoring documents...' :
                   newProgress < 75 ? 'Restoring configurations...' :
                   'Finalizing restore...'
          }
        })
      }, 1500)

      // This would call a restore backup API endpoint
      // await apiClient.restoreBackup(backupId)

      setTimeout(() => {
        clearInterval(progressInterval)
        setCurrentOperation({
          type: 'restore',
          progress: 100,
          status: 'Restore completed successfully!'
        })

        setTimeout(() => setCurrentOperation(null), 2000)
      }, 12000)

      setShowRestoreDialog(false)
      setSelectedBackup(null)
    } catch (error) {
      console.error('Failed to restore backup:', error)
      setCurrentOperation(null)
    }
  }

  const toggleSchedule = async (scheduleId: string, enabled: boolean) => {
    try {
      setSchedules(prev =>
        prev.map(schedule =>
          schedule.id === scheduleId
            ? { ...schedule, enabled }
            : schedule
        )
      )
      // This would call an update schedule API endpoint
      // await apiClient.updateBackupSchedule(scheduleId, { enabled })
    } catch (error) {
      console.error('Failed to update backup schedule:', error)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'in_progress': return <RefreshCw className="w-4 h-4 text-blue-500 animate-spin" />
      case 'failed': return <XCircle className="w-4 h-4 text-red-500" />
      case 'scheduled': return <Clock className="w-4 h-4 text-gray-500" />
      default: return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'completed': return 'default'
      case 'in_progress': return 'secondary'
      case 'failed': return 'destructive'
      case 'scheduled': return 'outline'
      default: return 'outline'
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'full': return <Database className="w-4 h-4" />
      case 'incremental': return <HardDrive className="w-4 h-4" />
      case 'configuration': return <Settings className="w-4 h-4" />
      default: return <Archive className="w-4 h-4" />
    }
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
                <span className="ml-2">Loading backup data...</span>
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
                <h1 className="text-3xl font-bold">Backup & Restore</h1>
                <p className="text-muted-foreground">Manage data backups and system restoration</p>
              </div>
              <div className="flex space-x-2">
                <Dialog open={showCreateBackup} onOpenChange={setShowCreateBackup}>
                  <DialogTrigger asChild>
                    <Button>
                      <Database className="w-4 h-4 mr-2" />
                      Create Backup
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Create New Backup</DialogTitle>
                      <DialogDescription>
                        Choose the type of backup you want to create
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <Button
                        onClick={() => createBackup('full')}
                        className="justify-start h-auto p-4"
                        variant="outline"
                      >
                        <Database className="w-5 h-5 mr-3" />
                        <div className="text-left">
                          <div className="font-medium">Full Backup</div>
                          <div className="text-sm text-muted-foreground">
                            Complete backup of all data, documents, and configurations
                          </div>
                        </div>
                      </Button>
                      <Button
                        onClick={() => createBackup('incremental')}
                        className="justify-start h-auto p-4"
                        variant="outline"
                      >
                        <HardDrive className="w-5 h-5 mr-3" />
                        <div className="text-left">
                          <div className="font-medium">Incremental Backup</div>
                          <div className="text-sm text-muted-foreground">
                            Backup only changes since last full backup
                          </div>
                        </div>
                      </Button>
                      <Button
                        onClick={() => createBackup('configuration')}
                        className="justify-start h-auto p-4"
                        variant="outline"
                      >
                        <Settings className="w-5 h-5 mr-3" />
                        <div className="text-left">
                          <div className="font-medium">Configuration Backup</div>
                          <div className="text-sm text-muted-foreground">
                            Backup only system configurations and settings
                          </div>
                        </div>
                      </Button>
                    </div>
                  </DialogContent>
                </Dialog>
              </div>
            </div>

            {/* Current Operation Progress */}
            {currentOperation && (
              <Card className="mb-6">
                <CardContent className="pt-6">
                  <div className="flex items-center space-x-4">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        {currentOperation.type === 'backup' ? (
                          <Database className="w-5 h-5" />
                        ) : (
                          <Upload className="w-5 h-5" />
                        )}
                        <span className="font-medium capitalize">{currentOperation.type} in Progress</span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-2">{currentOperation.status}</p>
                      <Progress value={currentOperation.progress} className="w-full" />
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold">{Math.round(currentOperation.progress)}%</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="grid lg:grid-cols-2 gap-6">
              {/* Backup History */}
              <Card>
                <CardHeader>
                  <CardTitle>Backup History</CardTitle>
                  <CardDescription>Recent backups and their status</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {backups.map((backup) => (
                      <div key={backup.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center space-x-4">
                          {getTypeIcon(backup.type)}
                          <div>
                            <h4 className="font-medium">{backup.name}</h4>
                            <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                              <span>{new Date(backup.createdAt).toLocaleDateString()}</span>
                              {backup.size > 0 && <span>• {formatFileSize(backup.size)}</span>}
                              {backup.scheduledFor && (
                                <span>• Scheduled for {new Date(backup.scheduledFor).toLocaleString()}</span>
                              )}
                            </div>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {backup.includes.slice(0, 3).map((item) => (
                                <Badge key={item} variant="outline" className="text-xs">
                                  {item}
                                </Badge>
                              ))}
                              {backup.includes.length > 3 && (
                                <Badge variant="outline" className="text-xs">
                                  +{backup.includes.length - 3}
                                </Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={getStatusBadgeVariant(backup.status)}>
                            {backup.status.replace('_', ' ')}
                          </Badge>
                          {backup.downloadUrl && backup.status === 'completed' && (
                            <Button size="sm" variant="outline">
                              <Download className="w-4 h-4" />
                            </Button>
                          )}
                          {backup.status === 'completed' && backup.type !== 'configuration' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setSelectedBackup(backup)
                                setShowRestoreDialog(true)
                              }}
                            >
                              <Upload className="w-4 h-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Backup Schedules */}
              <Card>
                <CardHeader>
                  <CardTitle>Scheduled Backups</CardTitle>
                  <CardDescription>Automated backup schedules</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {schedules.map((schedule) => (
                      <div key={schedule.id} className="flex items-center justify-between p-4 border rounded-lg">
                        <div className="flex items-center space-x-4">
                          {getTypeIcon(schedule.type)}
                          <div>
                            <h4 className="font-medium">{schedule.name}</h4>
                            <div className="text-sm text-muted-foreground">
                              {schedule.frequency} at {schedule.time}
                            </div>
                            <div className="text-xs text-muted-foreground mt-1">
                              Next run: {new Date(schedule.nextRun).toLocaleString()}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2">
                          <Badge variant={schedule.enabled ? 'default' : 'secondary'}>
                            {schedule.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => toggleSchedule(schedule.id, !schedule.enabled)}
                          >
                            {schedule.enabled ? 'Disable' : 'Enable'}
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Storage Information */}
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>Storage Information</CardTitle>
                <CardDescription>Backup storage usage and retention</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid md:grid-cols-3 gap-6">
                  <div className="text-center">
                    <Database className="w-8 h-8 mx-auto mb-2 text-blue-500" />
                    <div className="text-2xl font-bold">2.3 GB</div>
                    <div className="text-sm text-muted-foreground">Total Backup Size</div>
                  </div>
                  <div className="text-center">
                    <Archive className="w-8 h-8 mx-auto mb-2 text-green-500" />
                    <div className="text-2xl font-bold">45</div>
                    <div className="text-sm text-muted-foreground">Backup Files</div>
                  </div>
                  <div className="text-center">
                    <Calendar className="w-8 h-8 mx-auto mb-2 text-purple-500" />
                    <div className="text-2xl font-bold">30 days</div>
                    <div className="text-sm text-muted-foreground">Retention Period</div>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Restore Confirmation Dialog */}
            <Dialog open={showRestoreDialog} onOpenChange={setShowRestoreDialog}>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Confirm Restore</DialogTitle>
                  <DialogDescription>
                    Are you sure you want to restore from this backup? This action cannot be undone and may temporarily disrupt service.
                  </DialogDescription>
                </DialogHeader>
                {selectedBackup && (
                  <div className="py-4">
                    <div className="p-4 bg-muted rounded-lg">
                      <h4 className="font-medium mb-2">{selectedBackup.name}</h4>
                      <div className="text-sm text-muted-foreground space-y-1">
                        <div>Type: {selectedBackup.type}</div>
                        <div>Size: {formatFileSize(selectedBackup.size)}</div>
                        <div>Created: {new Date(selectedBackup.createdAt).toLocaleString()}</div>
                        <div>Includes: {selectedBackup.includes.join(', ')}</div>
                      </div>
                    </div>
                    <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                      <div className="flex items-center space-x-2">
                        <AlertTriangle className="w-5 h-5 text-yellow-600" />
                        <div>
                          <div className="font-medium text-yellow-800">Warning</div>
                          <div className="text-sm text-yellow-700">
                            Restoring from backup will overwrite current data. Ensure you have a recent backup before proceeding.
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setShowRestoreDialog(false)}>
                    Cancel
                  </Button>
                  <Button
                    onClick={() => selectedBackup && restoreBackup(selectedBackup.id)}
                    className="bg-red-600 hover:bg-red-700"
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    Restore Backup
                  </Button>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </div>
    </div>
  )
}