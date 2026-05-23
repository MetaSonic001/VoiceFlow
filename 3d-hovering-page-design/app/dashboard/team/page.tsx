'use client'

import { Button } from '@/components/ui/button'
import { Plus, Trash2 } from 'lucide-react'

export default function TeamPage() {
  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Team Management
          </h1>
          <p className="text-muted-foreground font-mono">
            Manage team members and permissions
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Invite Member
        </Button>
      </div>

      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-background border-b border-border">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Name</th>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Email</th>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Role</th>
                <th className="px-6 py-4 text-left text-sm font-mono font-semibold text-muted-foreground uppercase">Joined</th>
                <th className="px-6 py-4 text-right text-sm font-mono font-semibold text-muted-foreground uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {[
                { name: 'Admin User', email: 'admin@example.com', role: 'Owner', joined: '2023-01-01' },
                { name: 'John Doe', email: 'john@example.com', role: 'Admin', joined: '2023-06-15' },
                { name: 'Jane Smith', email: 'jane@example.com', role: 'Member', joined: '2023-09-20' },
              ].map((member, i) => (
                <tr key={i} className="hover:bg-background/50 transition-colors">
                  <td className="px-6 py-4 text-sm font-serif font-semibold text-foreground">{member.name}</td>
                  <td className="px-6 py-4 text-sm text-muted-foreground">{member.email}</td>
                  <td className="px-6 py-4 text-sm text-foreground">
                    <span className="bg-secondary px-2 py-1 rounded font-mono text-xs">{member.role}</span>
                  </td>
                  <td className="px-6 py-4 text-sm text-muted-foreground font-mono">{member.joined}</td>
                  <td className="px-6 py-4 text-right">
                    {i !== 0 && (
                      <Button variant="outline" size="sm" className="hover:border-red-500 hover:text-red-600">
                        <Trash2 size={14} />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
