"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Bell,
  BellOff,
  AlertTriangle,
  CheckCircle,
  Info,
  X,
  Settings,
  Mail,
  MessageSquare,
  Smartphone,
  Volume2,
  VolumeX,
  Trash2
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface Notification {
  id: string
  title: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
  category: 'system' | 'security' | 'usage' | 'billing' | 'support'
  read: boolean
  createdAt: string
  actionUrl?: string
  actionText?: string
}

interface NotificationSettings {
  emailNotifications: boolean
  pushNotifications: boolean
  smsNotifications: boolean
  soundEnabled: boolean
  categories: {
    system: boolean
    security: boolean
    usage: boolean
    billing: boolean
    support: boolean
  }
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [settings, setSettings] = useState<NotificationSettings>({
    emailNotifications: true,
    pushNotifications: false,
    smsNotifications: false,
    soundEnabled: true,
    categories: {
      system: true,
      security: true,
      usage: true,
      billing: true,
      support: true
    }
  })
  const [activeTab, setActiveTab] = useState('all')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadNotifications()
    loadSettings()
  }, [])

  const loadNotifications = async () => {
    try {
      setLoading(true)
      // This would call a notifications API endpoint
      // const data = await apiClient.getNotifications()
      // For now, using mock data
      const mockNotifications: Notification[] = [
        {
          id: 'notif-001',
          title: 'System Maintenance Scheduled',
          message: 'Scheduled maintenance will occur tonight from 2:00 AM to 4:00 AM EST. Some services may be temporarily unavailable.',
          type: 'info',
          category: 'system',
          read: false,
          createdAt: '2024-01-15T10:30:00Z',
          actionUrl: '/dashboard/system',
          actionText: 'View Status'
        },
        {
          id: 'notif-002',
          title: 'Security Alert: Failed Login Attempts',
          message: 'Multiple failed login attempts detected from IP address 192.168.1.100. Please review your account security.',
          type: 'warning',
          category: 'security',
          read: false,
          createdAt: '2024-01-15T09:15:00Z',
          actionUrl: '/dashboard/settings',
          actionText: 'Review Security'
        },
        {
          id: 'notif-003',
          title: 'Usage Limit Approaching',
          message: 'You have used 85% of your monthly API call limit. Consider upgrading your plan to avoid service interruption.',
          type: 'warning',
          category: 'usage',
          read: true,
          createdAt: '2024-01-14T16:45:00Z',
          actionUrl: '/dashboard/billing',
          actionText: 'View Usage'
        },
        {
          id: 'notif-004',
          title: 'Payment Processed Successfully',
          message: 'Your monthly subscription payment of $49.99 has been processed successfully.',
          type: 'success',
          category: 'billing',
          read: true,
          createdAt: '2024-01-14T12:00:00Z'
        },
        {
          id: 'notif-005',
          title: 'New Feature Available',
          message: 'Advanced analytics dashboard is now available! Check out the new insights and reporting features.',
          type: 'info',
          category: 'system',
          read: false,
          createdAt: '2024-01-13T14:20:00Z',
          actionUrl: '/dashboard/analytics',
          actionText: 'Explore Features'
        },
        {
          id: 'notif-006',
          title: 'Support Ticket Resolved',
          message: 'Your support ticket #12345 has been resolved. The agent configuration issue has been fixed.',
          type: 'success',
          category: 'support',
          read: true,
          createdAt: '2024-01-12T11:30:00Z'
        }
      ]
      setNotifications(mockNotifications)
    } catch (error) {
      console.error('Failed to load notifications:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadSettings = async () => {
    try {
      // This would call a notification settings API endpoint
      // const data = await apiClient.getNotificationSettings()
      // For now, using the default settings
    } catch (error) {
      console.error('Failed to load notification settings:', error)
    }
  }

  const updateSettings = async (newSettings: Partial<NotificationSettings>) => {
    try {
      const updatedSettings = { ...settings, ...newSettings }
      setSettings(updatedSettings)
      // This would call an update settings API endpoint
      // await apiClient.updateNotificationSettings(updatedSettings)
    } catch (error) {
      console.error('Failed to update notification settings:', error)
    }
  }

  const markAsRead = async (notificationId: string) => {
    try {
      setNotifications(prev =>
        prev.map(notif =>
          notif.id === notificationId ? { ...notif, read: true } : notif
        )
      )
      // This would call a mark as read API endpoint
      // await apiClient.markNotificationAsRead(notificationId)
    } catch (error) {
      console.error('Failed to mark notification as read:', error)
    }
  }

  const markAllAsRead = async () => {
    try {
      setNotifications(prev =>
        prev.map(notif => ({ ...notif, read: true }))
      )
      // This would call a mark all as read API endpoint
      // await apiClient.markAllNotificationsAsRead()
    } catch (error) {
      console.error('Failed to mark all notifications as read:', error)
    }
  }

  const deleteNotification = async (notificationId: string) => {
    try {
      setNotifications(prev => prev.filter(notif => notif.id !== notificationId))
      // This would call a delete notification API endpoint
      // await apiClient.deleteNotification(notificationId)
    } catch (error) {
      console.error('Failed to delete notification:', error)
    }
  }

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'success': return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'warning': return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      case 'error': return <X className="w-5 h-5 text-red-500" />
      default: return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'system': return 'bg-blue-100 text-blue-800'
      case 'security': return 'bg-red-100 text-red-800'
      case 'usage': return 'bg-yellow-100 text-yellow-800'
      case 'billing': return 'bg-green-100 text-green-800'
      case 'support': return 'bg-purple-100 text-purple-800'
      default: return 'bg-gray-100 text-gray-800'
    }
  }

  const filteredNotifications = notifications.filter(notif => {
    if (activeTab === 'all') return true
    if (activeTab === 'unread') return !notif.read
    return notif.category === activeTab
  })

  const unreadCount = notifications.filter(n => !n.read).length

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <div className="p-6">
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-2">Loading notifications...</span>
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
                <h1 className="text-3xl font-bold">Notifications</h1>
                <p className="text-muted-foreground">Stay updated with system alerts and messages</p>
              </div>
              {unreadCount > 0 && (
                <Button onClick={markAllAsRead} variant="outline">
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Mark All as Read ({unreadCount})
                </Button>
              )}

            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-7">
                <TabsTrigger value="all">
                  All
                  {notifications.length > 0 && (
                    <Badge variant="secondary" className="ml-2">
                      {notifications.length}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="unread">
                  Unread
                  {unreadCount > 0 && (
                    <Badge variant="destructive" className="ml-2">
                      {unreadCount}
                    </Badge>
                  )}
                </TabsTrigger>
                <TabsTrigger value="system">System</TabsTrigger>
                <TabsTrigger value="security">Security</TabsTrigger>
                <TabsTrigger value="usage">Usage</TabsTrigger>
                <TabsTrigger value="billing">Billing</TabsTrigger>
                <TabsTrigger value="support">Support</TabsTrigger>
              </TabsList>

              <TabsContent value={activeTab} className="mt-6">
                <div className="grid lg:grid-cols-3 gap-6">
                  {/* Notifications List */}
                  <div className="lg:col-span-2">
                    <Card>
                      <CardHeader>
                        <CardTitle>Recent Notifications</CardTitle>
                        <CardDescription>
                          {filteredNotifications.length} notification{filteredNotifications.length !== 1 ? 's' : ''}
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ScrollArea className="h-[600px]">
                          <div className="space-y-4">
                            {filteredNotifications.map((notification) => (
                              <div
                                key={notification.id}
                                className={`p-4 border rounded-lg transition-colors ${
                                  !notification.read ? 'bg-blue-50 border-blue-200' : 'bg-white'
                                }`}
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex items-start space-x-3">
                                    {getTypeIcon(notification.type)}
                                    <div className="flex-1">
                                      <div className="flex items-center space-x-2 mb-1">
                                        <h4 className="font-medium">{notification.title}</h4>
                                        <Badge className={getCategoryColor(notification.category)}>
                                          {notification.category}
                                        </Badge>
                                        {!notification.read && (
                                          <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                                        )}
                                      </div>
                                      <p className="text-sm text-muted-foreground mb-2">
                                        {notification.message}
                                      </p>
                                      <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                                        <span>{new Date(notification.createdAt).toLocaleString()}</span>
                                        {notification.actionUrl && (
                                          <a
                                            href={notification.actionUrl}
                                            className="text-blue-600 hover:text-blue-800"
                                          >
                                            {notification.actionText}
                                          </a>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <div className="flex space-x-1">
                                    {!notification.read && (
                                      <Button
                                        size="sm"
                                        variant="ghost"
                                        onClick={() => markAsRead(notification.id)}
                                      >
                                        <CheckCircle className="w-4 h-4" />
                                      </Button>
                                    )}
                                    <Button
                                      size="sm"
                                      variant="ghost"
                                      onClick={() => deleteNotification(notification.id)}
                                    >
                                      <Trash2 className="w-4 h-4" />
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            ))}
                            {filteredNotifications.length === 0 && (
                              <div className="text-center py-8">
                                <BellOff className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                                <h3 className="text-lg font-medium mb-2">No notifications</h3>
                                <p className="text-muted-foreground">
                                  {activeTab === 'unread'
                                    ? "You're all caught up!"
                                    : `No ${activeTab} notifications at this time.`
                                  }
                                </p>
                              </div>
                            )}
                          </div>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  </div>

                  {/* Settings Panel */}
                  <div>
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center">
                          <Settings className="w-5 h-5 mr-2" />
                          Notification Settings
                        </CardTitle>
                        <CardDescription>
                          Configure how you receive notifications
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="space-y-6">
                        {/* Delivery Methods */}
                        <div>
                          <h4 className="font-medium mb-3">Delivery Methods</h4>
                          <div className="space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <Mail className="w-4 h-4" />
                                <span className="text-sm">Email notifications</span>
                              </div>
                              <Switch
                                checked={settings.emailNotifications}
                                onCheckedChange={(checked) =>
                                  updateSettings({ emailNotifications: checked })
                                }
                              />
                            </div>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <Smartphone className="w-4 h-4" />
                                <span className="text-sm">Push notifications</span>
                              </div>
                              <Switch
                                checked={settings.pushNotifications}
                                onCheckedChange={(checked) =>
                                  updateSettings({ pushNotifications: checked })
                                }
                              />
                            </div>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                <MessageSquare className="w-4 h-4" />
                                <span className="text-sm">SMS notifications</span>
                              </div>
                              <Switch
                                checked={settings.smsNotifications}
                                onCheckedChange={(checked) =>
                                  updateSettings({ smsNotifications: checked })
                                }
                              />
                            </div>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center space-x-2">
                                {settings.soundEnabled ? (
                                  <Volume2 className="w-4 h-4" />
                                ) : (
                                  <VolumeX className="w-4 h-4" />
                                )}
                                <span className="text-sm">Sound alerts</span>
                              </div>
                              <Switch
                                checked={settings.soundEnabled}
                                onCheckedChange={(checked) =>
                                  updateSettings({ soundEnabled: checked })
                                }
                              />
                            </div>
                          </div>
                        </div>

                        {/* Categories */}
                        <div>
                          <h4 className="font-medium mb-3">Notification Categories</h4>
                          <div className="space-y-3">
                            {Object.entries(settings.categories).map(([category, enabled]) => (
                              <div key={category} className="flex items-center justify-between">
                                <span className="text-sm capitalize">{category}</span>
                                <Switch
                                  checked={enabled}
                                  onCheckedChange={(checked) =>
                                    updateSettings({
                                      categories: {
                                        ...settings.categories,
                                        [category]: checked
                                      }
                                    })
                                  }
                                />
                              </div>
                            ))}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    )
  }