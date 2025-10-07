"use client"

import React from "react"

export default function MorphingBlob({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 600 600"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      <defs>
        <linearGradient id="g" x1="0" x2="1">
          <stop offset="0%" stopColor="#7c3aed" />
          <stop offset="100%" stopColor="#06b6d4" />
        </linearGradient>
      </defs>
      <g transform="translate(300,300)">
        <path fill="url(#g)">
          <animate attributeName="d" dur="8s" repeatCount="indefinite"
            values="M120,-150C170,-120,210,-60,210,-10C210,40,170,90,120,120C70,150,10,170,-30,150C-70,130,-100,80,-120,30C-140,-20,-150,-80,-120,-120C-90,-160,-40,-180,10,-190C60,-200,120,-180,120,-150Z;M150,-130C190,-80,210,-10,180,30C150,70,90,90,30,120C-30,150,-90,170,-130,140C-170,110,-200,60,-190,10C-180,-40,-130,-90,-90,-130C-50,-170,-10,-190,40,-190C90,-190,110,-180,150,-130Z;M120,-150C170,-120,210,-60,210,-10C210,40,170,90,120,120C70,150,10,170,-30,150C-70,130,-100,80,-120,30C-140,-20,-150,-80,-120,-120C-90,-160,-40,-180,10,-190C60,-200,120,-180,120,-150Z"
          />
        </path>
      </g>
    </svg>
  )
}
