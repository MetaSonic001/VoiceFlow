'use client'

import dynamic from 'next/dynamic'

const ComputerScene = dynamic(
  () => import('@/components/landing/computer-scene'),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full flex items-center justify-center">
        <div className="font-mono text-sm text-stone-500">Loading 3D scene...</div>
      </div>
    ),
  },
)

interface ComputerSceneWrapperProps {
  mouseX: number
}

export function ComputerSceneWrapper({ mouseX }: ComputerSceneWrapperProps) {
  return <ComputerScene mouseX={mouseX} />
}
