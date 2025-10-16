"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { DashboardSidebar } from "@/components/dashboard/sidebar"
import {
  CreditCard,
  DollarSign,
  TrendingUp,
  TrendingDown,
  Calendar,
  Download,
  Receipt,
  AlertTriangle,
  CheckCircle,
  Clock,
  Zap,
  Bot,
  Phone,
  Database,
  FileText,
  BarChart3
} from "lucide-react"
import { apiClient } from "@/lib/api-client"

interface UsageMetrics {
  currentMonth: {
    apiCalls: number
    voiceMinutes: number
    storageGB: number
    agentInteractions: number
  }
  limits: {
    apiCalls: number
    voiceMinutes: number
    storageGB: number
    agentInteractions: number
  }
  costs: {
    apiCalls: number
    voiceMinutes: number
    storage: number
    total: number
  }
}

interface BillingHistory {
  id: string
  date: string
  description: string
  amount: number
  status: 'paid' | 'pending' | 'failed'
  invoiceUrl?: string
}

interface SubscriptionPlan {
  id: string
  name: string
  price: number
  period: 'monthly' | 'yearly'
  features: string[]
  limits: {
    apiCalls: number
    voiceMinutes: number
    storageGB: number
    agents: number
  }
  current: boolean
}

export default function BillingPage() {
  const [usage, setUsage] = useState<UsageMetrics | null>(null)
  const [billingHistory, setBillingHistory] = useState<BillingHistory[]>([])
  const [plans, setPlans] = useState<SubscriptionPlan[]>([])
  const [currentPlan, setCurrentPlan] = useState<SubscriptionPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedPeriod, setSelectedPeriod] = useState('current')

  useEffect(() => {
    loadBillingData()
  }, [])

  const loadBillingData = async () => {
    try {
      setLoading(true)
      // This would call billing API endpoints
      // const usageData = await apiClient.getUsageMetrics()
      // const historyData = await apiClient.getBillingHistory()
      // const plansData = await apiClient.getSubscriptionPlans()

      // Mock data for now
      const mockUsage: UsageMetrics = {
        currentMonth: {
          apiCalls: 125000,
          voiceMinutes: 2400,
          storageGB: 15.7,
          agentInteractions: 8900
        },
        limits: {
          apiCalls: 200000,
          voiceMinutes: 5000,
          storageGB: 50,
          agentInteractions: 15000
        },
        costs: {
          apiCalls: 125.00,
          voiceMinutes: 480.00,
          storage: 78.50,
          total: 683.50
        }
      }

      const mockHistory: BillingHistory[] = [
        {
          id: 'inv-001',
          date: '2024-01-01',
          description: 'Monthly Subscription - Pro Plan',
          amount: 299.00,
          status: 'paid',
          invoiceUrl: '/invoices/inv-001.pdf'
        },
        {
          id: 'inv-002',
          date: '2023-12-01',
          description: 'Monthly Subscription - Pro Plan',
          amount: 299.00,
          status: 'paid',
          invoiceUrl: '/invoices/inv-002.pdf'
        },
        {
          id: 'inv-003',
          date: '2023-11-15',
          description: 'Usage Overage - API Calls',
          amount: 45.50,
          status: 'paid',
          invoiceUrl: '/invoices/inv-003.pdf'
        },
        {
          id: 'inv-004',
          date: '2024-01-15',
          description: 'Usage Overage - Voice Minutes',
          amount: 120.00,
          status: 'pending'
        }
      ]

      const mockPlans: SubscriptionPlan[] = [
        {
          id: 'starter',
          name: 'Starter',
          price: 49,
          period: 'monthly',
          features: ['5 AI Agents', '10K API Calls', '100 Voice Minutes', '5GB Storage'],
          limits: {
            apiCalls: 10000,
            voiceMinutes: 100,
            storageGB: 5,
            agents: 5
          },
          current: false
        },
        {
          id: 'pro',
          name: 'Professional',
          price: 299,
          period: 'monthly',
          features: ['Unlimited AI Agents', '200K API Calls', '5K Voice Minutes', '50GB Storage', 'Advanced Analytics', 'Priority Support'],
          limits: {
            apiCalls: 200000,
            voiceMinutes: 5000,
            storageGB: 50,
            agents: -1 // unlimited
          },
          current: true
        },
        {
          id: 'enterprise',
          name: 'Enterprise',
          price: 999,
          period: 'monthly',
          features: ['Everything in Pro', 'Custom Integrations', 'Dedicated Support', 'SLA Guarantee', 'Custom Training'],
          limits: {
            apiCalls: -1, // unlimited
            voiceMinutes: -1, // unlimited
            storageGB: -1, // unlimited
            agents: -1 // unlimited
          },
          current: false
        }
      ]

      setUsage(mockUsage)
      setBillingHistory(mockHistory)
      setPlans(mockPlans)
      setCurrentPlan(mockPlans.find(p => p.current) || null)
    } catch (error) {
      console.error('Failed to load billing data:', error)
    } finally {
      setLoading(false)
    }
  }

  const upgradePlan = async (planId: string) => {
    try {
      // This would call an upgrade plan API endpoint
      // await apiClient.upgradePlan(planId)
      alert(`Plan upgrade to ${planId} initiated. You will be charged the prorated amount.`)
    } catch (error) {
      console.error('Failed to upgrade plan:', error)
    }
  }

  const downloadInvoice = async (invoiceId: string) => {
    try {
      // This would call a download invoice API endpoint
      // await apiClient.downloadInvoice(invoiceId)
      alert('Invoice download initiated')
    } catch (error) {
      console.error('Failed to download invoice:', error)
    }
  }

  const getUsagePercentage = (current: number, limit: number) => {
    if (limit === -1) return 0 // unlimited
    return Math.min((current / limit) * 100, 100)
  }

  const getUsageColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500'
    if (percentage >= 75) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD'
    }).format(amount)
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid': return <CheckCircle className="w-4 h-4 text-green-500" />
      case 'pending': return <Clock className="w-4 h-4 text-yellow-500" />
      case 'failed': return <AlertTriangle className="w-4 h-4 text-red-500" />
      default: return <Clock className="w-4 h-4 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (status: string) => {
    switch (status) {
      case 'paid': return 'default'
      case 'pending': return 'secondary'
      case 'failed': return 'destructive'
      default: return 'outline'
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
                <span className="ml-2">Loading billing data...</span>
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
                <h1 className="text-3xl font-bold">Billing & Usage</h1>
                <p className="text-muted-foreground">Monitor your usage and manage billing</p>
              </div>
              <div className="flex space-x-2">
                <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="current">Current Month</SelectItem>
                    <SelectItem value="last">Last Month</SelectItem>
                    <SelectItem value="last3">Last 3 Months</SelectItem>
                  </SelectContent>
                </Select>
                <Button variant="outline">
                  <Download className="w-4 h-4 mr-2" />
                  Export Report
                </Button>
              </div>
            </div>

            <Tabs defaultValue="usage" className="space-y-6">
              <TabsList>
                <TabsTrigger value="usage">Usage & Limits</TabsTrigger>
                <TabsTrigger value="billing">Billing History</TabsTrigger>
                <TabsTrigger value="plans">Subscription Plans</TabsTrigger>
              </TabsList>

              <TabsContent value="usage" className="space-y-6">
                {/* Current Usage Overview */}
                <div className="grid lg:grid-cols-4 gap-6">
                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">API Calls</p>
                          <p className="text-2xl font-bold">
                            {usage?.currentMonth.apiCalls.toLocaleString()}
                            {usage?.limits.apiCalls !== -1 && ` / ${usage?.limits.apiCalls.toLocaleString()}`}
                          </p>
                        </div>
                        <Zap className="w-8 h-8 text-blue-500" />
                      </div>
                      {usage && usage.limits.apiCalls !== -1 && (
                        <div className="mt-4">
                          <Progress
                            value={getUsagePercentage(usage.currentMonth.apiCalls, usage.limits.apiCalls)}
                            className="h-2"
                          />
                          <p className="text-xs text-muted-foreground mt-1">
                            {Math.round(getUsagePercentage(usage.currentMonth.apiCalls, usage.limits.apiCalls))}% used
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Voice Minutes</p>
                          <p className="text-2xl font-bold">
                            {usage?.currentMonth.voiceMinutes.toLocaleString()}
                            {usage?.limits.voiceMinutes !== -1 && ` / ${usage?.limits.voiceMinutes.toLocaleString()}`}
                          </p>
                        </div>
                        <Phone className="w-8 h-8 text-green-500" />
                      </div>
                      {usage && usage.limits.voiceMinutes !== -1 && (
                        <div className="mt-4">
                          <Progress
                            value={getUsagePercentage(usage.currentMonth.voiceMinutes, usage.limits.voiceMinutes)}
                            className="h-2"
                          />
                          <p className="text-xs text-muted-foreground mt-1">
                            {Math.round(getUsagePercentage(usage.currentMonth.voiceMinutes, usage.limits.voiceMinutes))}% used
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Storage Used</p>
                          <p className="text-2xl font-bold">
                            {usage?.currentMonth.storageGB.toFixed(1)} GB
                            {usage?.limits.storageGB !== -1 && ` / ${usage?.limits.storageGB} GB`}
                          </p>
                        </div>
                        <Database className="w-8 h-8 text-purple-500" />
                      </div>
                      {usage && usage.limits.storageGB !== -1 && (
                        <div className="mt-4">
                          <Progress
                            value={getUsagePercentage(usage.currentMonth.storageGB, usage.limits.storageGB)}
                            className="h-2"
                          />
                          <p className="text-xs text-muted-foreground mt-1">
                            {Math.round(getUsagePercentage(usage.currentMonth.storageGB, usage.limits.storageGB))}% used
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  <Card>
                    <CardContent className="pt-6">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Agent Interactions</p>
                          <p className="text-2xl font-bold">
                            {usage?.currentMonth.agentInteractions.toLocaleString()}
                            {usage?.limits.agentInteractions !== -1 && ` / ${usage?.limits.agentInteractions.toLocaleString()}`}
                          </p>
                        </div>
                        <Bot className="w-8 h-8 text-orange-500" />
                      </div>
                      {usage && usage.limits.agentInteractions !== -1 && (
                        <div className="mt-4">
                          <Progress
                            value={getUsagePercentage(usage.currentMonth.agentInteractions, usage.limits.agentInteractions)}
                            className="h-2"
                          />
                          <p className="text-xs text-muted-foreground mt-1">
                            {Math.round(getUsagePercentage(usage.currentMonth.agentInteractions, usage.limits.agentInteractions))}% used
                          </p>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Cost Breakdown */}
                <Card>
                  <CardHeader>
                    <CardTitle>Current Month Costs</CardTitle>
                    <CardDescription>Breakdown of your usage costs</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Zap className="w-4 h-4 text-blue-500" />
                          <span>API Calls</span>
                        </div>
                        <span className="font-medium">{formatCurrency(usage?.costs.apiCalls || 0)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Phone className="w-4 h-4 text-green-500" />
                          <span>Voice Minutes</span>
                        </div>
                        <span className="font-medium">{formatCurrency(usage?.costs.voiceMinutes || 0)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <Database className="w-4 h-4 text-purple-500" />
                          <span>Storage</span>
                        </div>
                        <span className="font-medium">{formatCurrency(usage?.costs.storage || 0)}</span>
                      </div>
                      <div className="border-t pt-4">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">Total</span>
                          <span className="text-xl font-bold">{formatCurrency(usage?.costs.total || 0)}</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="billing" className="space-y-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Billing History</CardTitle>
                    <CardDescription>Your payment history and invoices</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {billingHistory.map((invoice) => (
                        <div key={invoice.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center space-x-4">
                            {getStatusIcon(invoice.status)}
                            <div>
                              <h4 className="font-medium">{invoice.description}</h4>
                              <div className="text-sm text-muted-foreground">
                                {new Date(invoice.date).toLocaleDateString()}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-4">
                            <span className="font-medium">{formatCurrency(invoice.amount)}</span>
                            <Badge variant={getStatusBadgeVariant(invoice.status)}>
                              {invoice.status}
                            </Badge>
                            {invoice.invoiceUrl && (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => downloadInvoice(invoice.id)}
                              >
                                <Receipt className="w-4 h-4" />
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="plans" className="space-y-6">
                <div className="grid lg:grid-cols-3 gap-6">
                  {plans.map((plan) => (
                    <Card key={plan.id} className={plan.current ? 'border-primary' : ''}>
                      <CardHeader>
                        <div className="flex items-center justify-between">
                          <CardTitle>{plan.name}</CardTitle>
                          {plan.current && <Badge>Current Plan</Badge>}
                        </div>
                        <div className="text-3xl font-bold">
                          {formatCurrency(plan.price)}
                          <span className="text-sm font-normal text-muted-foreground">/{plan.period}</span>
                        </div>
                      </CardHeader>
                      <CardContent>
                        <ul className="space-y-2 mb-6">
                          {plan.features.map((feature, index) => (
                            <li key={index} className="flex items-center space-x-2">
                              <CheckCircle className="w-4 h-4 text-green-500" />
                              <span className="text-sm">{feature}</span>
                            </li>
                          ))}
                        </ul>
                        {!plan.current && (
                          <Button
                            className="w-full"
                            onClick={() => upgradePlan(plan.id)}
                          >
                            Upgrade to {plan.name}
                          </Button>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>
            </Tabs>
          </div>
        </div>
      </div>
    </div>
  )
}