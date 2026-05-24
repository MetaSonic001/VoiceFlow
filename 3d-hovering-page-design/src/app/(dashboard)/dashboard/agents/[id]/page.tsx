import Link from 'next/link'

export default function AgentDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  return (
    <AgentDetail params={params} />
  )
}

async function AgentDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  return (
    <div className="p-8">
      <h1 className="text-4xl font-serif font-bold text-foreground mb-2">Agent Details</h1>
      <p className="font-mono text-muted-foreground mb-8">Agent ID: {id}</p>
      <Link href="/dashboard" className="font-mono text-sm text-accent hover:underline">
        Back to dashboard
      </Link>
    </div>
  )
}
