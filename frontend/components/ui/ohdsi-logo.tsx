import React from 'react'

interface OHDSILogoProps {
  className?: string
  width?: number
  height?: number
  showText?: boolean
}

export function OHDSILogo({ 
  className = '', 
  width = 120, 
  height = 40,
  showText = true 
}: OHDSILogoProps) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 120 40"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Logo Mark - Interconnected circles representing data networks */}
      <g>
        {/* Main circle - Blue */}
        <circle
          cx="16"
          cy="20"
          r="8"
          fill="hsl(210, 100%, 40%)"
          opacity="0.9"
        />
        {/* Overlapping circle - Gold */}
        <circle
          cx="22"
          cy="20"
          r="8"
          fill="hsl(45, 100%, 50%)"
          opacity="0.8"
        />
        {/* Center overlap effect */}
        <circle
          cx="19"
          cy="20"
          r="3"
          fill="hsl(210, 100%, 30%)"
        />
        {/* Data points */}
        <circle cx="16" cy="17" r="1" fill="white" />
        <circle cx="22" cy="23" r="1" fill="white" />
        <circle cx="19" cy="20" r="1" fill="white" />
      </g>

      {showText && (
        <g>
          {/* OHDSI Text */}
          <text
            x="36"
            y="24"
            fontFamily="Inter, system-ui, sans-serif"
            fontSize="16"
            fontWeight="700"
            fill="hsl(210, 100%, 40%)"
          >
            OHDSI
          </text>
          {/* Decorative gold dot */}
          <circle
            cx="110"
            cy="20"
            r="2"
            fill="hsl(45, 100%, 50%)"
          />
        </g>
      )}
    </svg>
  )
}

export function OHDSIIcon({ 
  className = '', 
  size = 32 
}: { 
  className?: string
  size?: number 
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
    >
      {/* Simplified icon version */}
      <circle
        cx="12"
        cy="16"
        r="10"
        fill="hsl(210, 100%, 40%)"
        opacity="0.9"
      />
      <circle
        cx="20"
        cy="16"
        r="10"
        fill="hsl(45, 100%, 50%)"
        opacity="0.8"
      />
      <circle
        cx="16"
        cy="16"
        r="4"
        fill="hsl(210, 100%, 30%)"
      />
      <circle cx="12" cy="14" r="1.5" fill="white" />
      <circle cx="20" cy="18" r="1.5" fill="white" />
      <circle cx="16" cy="16" r="1.5" fill="white" />
    </svg>
  )
}