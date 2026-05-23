'use client'

import { Button } from '@/components/ui/button'
import { Plus } from 'lucide-react'

export default function PhoneNumbersPage() {
  return (
    <div className="p-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-serif font-bold text-foreground mb-2">
            Phone Numbers
          </h1>
          <p className="text-muted-foreground font-mono">
            Manage your VoiceFlow phone numbers and routing
          </p>
        </div>
        <Button className="bg-accent hover:bg-accent/90">
          <Plus size={18} className="mr-2" />
          Add Phone Number
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {[
          { number: '+1 (555) 123-4567', country: 'United States', status: 'active', agent: 'Customer Support' },
          { number: '+1 (555) 987-6543', country: 'United States', status: 'active', agent: 'Sales Outreach' },
          { number: '+44 20 7946 0958', country: 'United Kingdom', status: 'inactive', agent: 'None' },
        ].map((phone) => (
          <div key={phone.number} className="bg-card border border-border rounded-lg p-6">
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-serif font-bold text-foreground">{phone.number}</h3>
                <p className="text-sm text-muted-foreground font-mono">{phone.country}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap ${
                phone.status === 'active' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
              }`}>
                {phone.status.charAt(0).toUpperCase() + phone.status.slice(1)}
              </span>
            </div>
            <div className="mb-4 pb-4 border-b border-border">
              <p className="text-sm text-muted-foreground font-mono uppercase mb-1">Assigned Agent</p>
              <p className="text-sm font-serif text-foreground">{phone.agent}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="flex-1">Edit</Button>
              <Button variant="outline" className="hover:border-red-500 hover:text-red-600">Delete</Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
