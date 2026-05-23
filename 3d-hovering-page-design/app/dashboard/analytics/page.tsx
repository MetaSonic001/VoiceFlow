'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'

const callData = [
  { date: 'Jan 15', calls: 234, completed: 198, failed: 36 },
  { date: 'Jan 16', calls: 289, completed: 245, failed: 44 },
  { date: 'Jan 17', calls: 267, completed: 228, failed: 39 },
  { date: 'Jan 18', calls: 345, completed: 298, failed: 47 },
  { date: 'Jan 19', calls: 432, completed: 378, failed: 54 },
  { date: 'Jan 20', calls: 456, completed: 401, failed: 55 },
]

const accuracyData = [
  { agent: 'Support', accuracy: 94 },
  { agent: 'Sales', accuracy: 88 },
  { agent: 'Scheduler', accuracy: 92 },
  { agent: 'Survey', accuracy: 85 },
]

export default function AnalyticsPage() {
  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
          Analytics
        </h1>
        <p className="text-muted-foreground font-mono">
          Performance metrics and insights
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-serif font-bold text-foreground mb-4">
            Call Volume (Last 7 days)
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={callData}>
              <CartesianGrid stroke="#e0dcd6" />
              <XAxis dataKey="date" stroke="#7a7571" />
              <YAxis stroke="#7a7571" />
              <Tooltip contentStyle={{ backgroundColor: '#f5f1ed', border: '1px solid #d4d0ca' }} />
              <Legend />
              <Line type="monotone" dataKey="completed" stroke="#8b6f47" strokeWidth={2} />
              <Line type="monotone" dataKey="failed" stroke="#c42e1e" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="bg-card border border-border rounded-lg p-6">
          <h2 className="text-lg font-serif font-bold text-foreground mb-4">
            Agent Accuracy
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={accuracyData}>
              <CartesianGrid stroke="#e0dcd6" />
              <XAxis dataKey="agent" stroke="#7a7571" />
              <YAxis stroke="#7a7571" />
              <Tooltip contentStyle={{ backgroundColor: '#f5f1ed', border: '1px solid #d4d0ca' }} />
              <Bar dataKey="accuracy" fill="#8b6f47" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
