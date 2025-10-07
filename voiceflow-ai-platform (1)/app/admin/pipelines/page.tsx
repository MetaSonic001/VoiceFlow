import React, { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'

export default function PipelineAdminPage() {
  const [pipelines, setPipelines] = useState<any[]>([])
  const [agents, setAgents] = useState<any[]>([])
  const [name, setName] = useState('')

  useEffect(() => {
    apiClient.listPipelines().then(r => setPipelines(r.pipelines || []))
    apiClient.listPipelineAgents().then(r => setAgents(r.pipeline_agents || []))
  }, [])

  const create = async () => {
    if (!name) return
    const res = await apiClient.createPipeline({ tenant_id: 'default', name, stages: [] })
    setName('')
    const list = await apiClient.listPipelines()
    setPipelines(list.pipelines || [])
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">Pipeline Admin</h1>
      <div className="mb-4">
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Pipeline name" className="border p-2 mr-2" />
        <button onClick={create} className="bg-blue-600 text-white px-3 py-2 rounded">Create</button>
      </div>

      <h2 className="text-xl font-semibold">Pipelines</h2>
      <ul>
        {pipelines.map(p => (
          <li key={p.id} className="border p-2 my-2">
            <div className="font-medium">{p.name}</div>
            <div className="text-sm text-gray-600">Stages: {Array.isArray(p.stages) ? p.stages.length : 0}</div>
            <button onClick={() => apiClient.triggerPipeline(p.id)} className="mt-2 bg-green-600 text-white px-2 py-1 rounded">Run</button>
          </li>
        ))}
      </ul>

      <h2 className="text-xl font-semibold mt-6">Pipeline Agents</h2>
      <ul>
        {agents.map(a => (
          <li key={a.id} className="border p-2 my-2">
            <div className="font-medium">{a.name} ({a.agent_type})</div>
            <div className="text-sm text-gray-600">Ref Agent: {a.agent_id || '—'}</div>
          </li>
        ))}
      </ul>
    </div>
  )
}
