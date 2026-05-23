'use client';

import { Canvas } from '@react-three/fiber';
import { PerspectiveCamera, OrbitControls } from '@react-three/drei';
import { useFrame, useThree } from '@react-three/fiber';
import { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface ComputerSceneProps {
  mouseX: number;
}

function RetroComputer({ mouseX }: ComputerSceneProps) {
  const groupRef = useRef<THREE.Group>(null);
  const screenMaterialRef = useRef<THREE.MeshBasicMaterial>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const animationRef = useRef(0);

  useFrame((state) => {
    if (groupRef.current) {
      // Rotate based on mouse X position
      groupRef.current.rotation.y = mouseX * 0.4;
    }

    // Animate the frequency lines
    if (screenMaterialRef.current && canvasRef.current) {
      animationRef.current += 0.08;
      const canvas = canvasRef.current;
      const newCanvas = createScreenTexture(animationRef.current);
      if (screenMaterialRef.current.map) {
        screenMaterialRef.current.map.dispose();
      }
      screenMaterialRef.current.map = new THREE.CanvasTexture(newCanvas);
      screenMaterialRef.current.map.needsUpdate = true;
      canvasRef.current = newCanvas;
    }
  });

  useEffect(() => {
    canvasRef.current = createScreenTexture(0);
  }, []);

  return (
    <group ref={groupRef}>
      {/* Main computer body - beige case */}
      <mesh position={[0, -0.1, 0]}>
        <boxGeometry args={[1.2, 1.6, 0.8]} />
        <meshPhongMaterial color="#f5f1ed" />
      </mesh>

      {/* Monitor bezel - rounded gray frame */}
      <mesh position={[0, 0.2, 0.42]}>
        <boxGeometry args={[1.1, 1.15, 0.1]} />
        <meshPhongMaterial color="#d0ccc8" />
      </mesh>

      {/* Monitor rounded corners effect - top */}
      <mesh position={[0, 0.8, 0.42]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshPhongMaterial color="#d0ccc8" />
      </mesh>

      {/* Monitor screen - curved CRT look */}
      <mesh position={[0, 0.2, 0.48]}>
        <planeGeometry args={[1.0, 1.0]} />
        <meshPhongMaterial color="#0a0a0a" />
      </mesh>

      {/* Screen content texture */}
      <mesh position={[0, 0.2, 0.481]}>
        <planeGeometry args={[1.0, 1.0]} />
        <meshBasicMaterial ref={screenMaterialRef}>
          <canvasTexture 
            attach="map"
            args={[createScreenTexture(0)]}
          />
        </meshBasicMaterial>
      </mesh>

      {/* Monitor bezel left edge */}
      <mesh position={[-0.6, 0.2, 0.45]}>
        <boxGeometry args={[0.05, 1.15, 0.15]} />
        <meshPhongMaterial color="#d0ccc8" />
      </mesh>

      {/* Monitor bezel right edge */}
      <mesh position={[0.6, 0.2, 0.45]}>
        <boxGeometry args={[0.05, 1.15, 0.15]} />
        <meshPhongMaterial color="#d0ccc8" />
      </mesh>

      {/* Monitor bottom bezel */}
      <mesh position={[0, -0.35, 0.42]}>
        <boxGeometry args={[1.1, 0.08, 0.1]} />
        <meshPhongMaterial color="#d0ccc8" />
      </mesh>

      {/* Black power button bar */}
      <mesh position={[0, -0.5, 0.42]}>
        <boxGeometry args={[0.6, 0.08, 0.08]} />
        <meshPhongMaterial color="#2a2a2a" />
      </mesh>

      {/* Keyboard base */}
      <mesh position={[0, -1.0, 0.3]}>
        <boxGeometry args={[1.4, 0.12, 0.5]} />
        <meshPhongMaterial color="#e8e4df" />
      </mesh>

      {/* Keyboard keys grid - 4 rows */}
      {Array.from({ length: 52 }).map((_, i) => {
        const row = Math.floor(i / 13);
        const col = i % 13;
        return (
          <mesh 
            key={`key-${i}`} 
            position={[col * 0.095 - 0.57, -0.95 + row * 0.025, 0.15]}
          >
            <boxGeometry args={[0.075, 0.02, 0.035]} />
            <meshPhongMaterial color="#f0ede8" />
          </mesh>
        );
      })}

      {/* Sticker 1: Orange/tan smiling face */}
      <group position={[-0.25, -0.15, 0.42]}>
        {/* Orange circle body */}
        <mesh position={[0, 0, 0.02]}>
          <circleGeometry args={[0.12, 32]} />
          <meshPhongMaterial color="#da6f42" />
        </mesh>
        {/* White overlay */}
        <mesh position={[0.06, 0, 0.025]}>
          <circleGeometry args={[0.08, 32]} />
          <meshPhongMaterial color="#ffffff" />
        </mesh>
        {/* Blue star */}
        <mesh position={[0.05, -0.02, 0.03]}>
          <boxGeometry args={[0.08, 0.08, 0.01]} />
          <meshPhongMaterial color="#1e3a8a" />
        </mesh>
      </group>

      {/* Sticker 2: Rainbow/colorful element */}
      <group position={[0.1, -0.05, 0.42]}>
        {/* Green top */}
        <mesh position={[0, 0.04, 0.01]}>
          <boxGeometry args={[0.08, 0.05, 0.01]} />
          <meshPhongMaterial color="#b8d4a8" />
        </mesh>
        {/* Yellow middle */}
        <mesh position={[0, 0, 0.01]}>
          <boxGeometry args={[0.08, 0.05, 0.01]} />
          <meshPhongMaterial color="#fcc34f" />
        </mesh>
        {/* Red bottom */}
        <mesh position={[0, -0.04, 0.01]}>
          <boxGeometry args={[0.08, 0.05, 0.01]} />
          <meshPhongMaterial color="#ef5350" />
        </mesh>
      </group>

      {/* Sticker 3: Dark red label */}
      <mesh position={[0.35, -0.1, 0.43]}>
        <boxGeometry args={[0.12, 0.06, 0.01]} />
        <meshPhongMaterial color="#8b1a1a" />
      </mesh>

      {/* Sticker 4: Small colorful dot pattern on keyboard */}
      <mesh position={[0.9, -1.0, 0.32]}>
        <boxGeometry args={[0.08, 0.08, 0.01]} />
        <meshPhongMaterial color="#2a2a2a" />
      </mesh>
    </group>
  );
}

function createScreenTexture(time: number = 0): HTMLCanvasElement {
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 480;

  const ctx = canvas.getContext('2d');
  if (!ctx) return canvas;

  // Black background
  ctx.fillStyle = '#0a0a0a';
  ctx.fillRect(0, 0, 640, 480);

  // Scan line effect
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.15)';
  ctx.lineWidth = 1;
  for (let i = 0; i < 480; i += 2) {
    ctx.beginPath();
    ctx.moveTo(0, i);
    ctx.lineTo(640, i);
    ctx.stroke();
  }

  // Left menu area - colored dots and text
  ctx.fillStyle = '#2563eb';
  ctx.font = 'bold 20px monospace';
  ctx.fillText('●', 40, 80);
  ctx.fillStyle = '#fff';
  ctx.font = '18px monospace';
  ctx.fillText('System', 80, 85);

  ctx.fillStyle = '#ff6b35';
  ctx.fillText('●', 40, 130);
  ctx.fillStyle = '#fff';
  ctx.fillText('Disk A', 80, 135);

  ctx.fillStyle = '#888';
  ctx.fillText('●', 40, 180);
  ctx.fillStyle = '#fff';
  ctx.fillText('Trash', 80, 185);

  ctx.fillStyle = '#888';
  ctx.fillText('●', 40, 230);
  ctx.fillStyle = '#fff';
  ctx.fillText('Write', 80, 235);

  ctx.fillStyle = '#888';
  ctx.fillText('●', 40, 280);
  ctx.fillStyle = '#fff';
  ctx.fillText('Think', 80, 285);

  // Right content area - file browser
  ctx.fillStyle = '#fff';
  ctx.font = 'bold 18px monospace';
  ctx.fillText('FigS 1.0', 350, 85);

  // File content box
  ctx.strokeStyle = '#ccc';
  ctx.lineWidth = 2;
  ctx.strokeRect(300, 120, 300, 120);

  ctx.fillStyle = '#fff';
  ctx.font = '16px monospace';
  ctx.fillText('untitled.txt', 320, 145);
  ctx.fillStyle = '#999';
  ctx.font = '14px monospace';
  ctx.fillText('[a]', 550, 145);

  ctx.fillStyle = '#fff';
  ctx.font = '15px monospace';
  ctx.fillText('Good morning. Your memo', 320, 175);
  ctx.fillText('is drafted.', 320, 200);

  // Animated waveform visualization - audio equalizer style
  const barCount = 90;
  const startX = 310;
  const startY = 300;
  const maxHeight = 110;
  const barWidth = 280 / barCount;
  const barSpacing = 2;

  // Create waveform data with sine waves and bass/treble variation
  for (let i = 0; i < barCount; i++) {
    // Multiple sine waves at different frequencies with faster animation
    const wave1 = Math.sin(time * 0.12 + i * 0.12) * 0.4;
    const wave2 = Math.sin(time * 0.15 + i * 0.08) * 0.35;
    const wave3 = Math.sin(time * 0.08 + i * 0.1) * 0.25;
    const bassBoost = Math.sin(time * 0.06 + (i - barCount / 2) * 0.04) * 0.4;
    const trebleBoost = Math.sin(time * 0.18 + i * 0.2) * 0.2;
    
    // Combine waves with more dynamic range
    let height = (wave1 + wave2 + wave3 + bassBoost + trebleBoost) * 0.5 + 0.35;
    height = Math.max(0.05, Math.min(1, height));
    
    const barHeight = height * maxHeight;
    const x = startX + i * barWidth + barWidth * 0.5;
    const topY = startY - barHeight;
    const bottomY = startY + barHeight;

    // Draw vertical bar with gradient effect
    const gradient = ctx.createLinearGradient(x, topY, x, bottomY);
    gradient.addColorStop(0, '#0066ff');
    gradient.addColorStop(0.3, '#00aaff');
    gradient.addColorStop(0.5, '#00ffff');
    gradient.addColorStop(0.7, '#00aaff');
    gradient.addColorStop(1, '#0066ff');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(x - barSpacing, topY, barSpacing * 2, barHeight * 2);
  }

  // Add bright glow effect
  ctx.globalAlpha = 0.4;
  for (let i = 0; i < barCount; i++) {
    const wave1 = Math.sin(time * 0.12 + i * 0.12) * 0.4;
    const wave2 = Math.sin(time * 0.15 + i * 0.08) * 0.35;
    const wave3 = Math.sin(time * 0.08 + i * 0.1) * 0.25;
    const bassBoost = Math.sin(time * 0.06 + (i - barCount / 2) * 0.04) * 0.4;
    const trebleBoost = Math.sin(time * 0.18 + i * 0.2) * 0.2;
    
    let height = (wave1 + wave2 + wave3 + bassBoost + trebleBoost) * 0.5 + 0.35;
    height = Math.max(0.05, Math.min(1, height));
    
    const barHeight = height * maxHeight;
    const x = startX + i * barWidth + barWidth * 0.5;
    const topY = startY - barHeight;
    const bottomY = startY + barHeight;

    ctx.fillStyle = '#00ffff';
    ctx.fillRect(x - barSpacing - 2, topY - 8, barSpacing * 2 + 4, barHeight * 2 + 16);
  }
  ctx.globalAlpha = 1.0;

  return canvas;
}

export default function ComputerScene({ mouseX }: ComputerSceneProps) {
  return (
    <Canvas style={{ width: '100%', height: '100%' }}>
      <PerspectiveCamera position={[0, -0.15, 2.8]} fov={45} makeDefault />
      <ambientLight intensity={0.6} />
      <directionalLight position={[5, 5, 5]} intensity={0.8} />
      <directionalLight position={[-5, 5, 5]} intensity={0.3} />
      
      <RetroComputer mouseX={mouseX} />
    </Canvas>
  );
}
