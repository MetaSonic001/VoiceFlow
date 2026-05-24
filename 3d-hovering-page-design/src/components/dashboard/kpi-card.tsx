import { LucideIcon } from 'lucide-react'

interface KPICardProps {
  icon: LucideIcon
  label: string
  value: string | number
  unit?: string
  trend?: {
    value: number
    isPositive: boolean
  }
  color?: 'default' | 'accent' | 'success' | 'warning' | 'error'
}

const colorClasses = {
  default: 'text-foreground',
  accent: 'text-accent',
  success: 'text-green-600',
  warning: 'text-yellow-600',
  error: 'text-red-600',
}

const bgColorClasses = {
  default: 'bg-card',
  accent: 'bg-accent/10',
  success: 'bg-green-50',
  warning: 'bg-yellow-50',
  error: 'bg-red-50',
}

export function KPICard({ icon: Icon, label, value, unit, trend, color = 'default' }: KPICardProps) {
  return (
    <div className={`${bgColorClasses[color]} border border-border rounded-lg p-6`}>
      <div className="flex items-start justify-between mb-4">
        <div className={`p-2 rounded-md ${colorClasses[color]} opacity-20 bg-foreground`}>
          <Icon size={24} className={colorClasses[color]} />
        </div>
        {trend && (
          <div className={`text-sm font-semibold ${trend.isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {trend.isPositive ? '+' : '-'}{Math.abs(trend.value)}%
          </div>
        )}
      </div>
      
      <p className="text-sm text-muted-foreground font-mono uppercase tracking-wider mb-2">
        {label}
      </p>
      
      <div className="flex items-baseline gap-2">
        <p className="text-3xl font-serif font-bold text-foreground">
          {value}
        </p>
        {unit && <p className="text-sm text-muted-foreground font-mono">{unit}</p>}
      </div>
    </div>
  )
}
