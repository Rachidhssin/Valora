import { motion } from 'framer-motion'

/**
 * RadarChart - SVG-based 4-axis radar chart for Financial DNA
 * 
 * Features:
 * - 4 labeled axes
 * - Animated data transitions
 * - Dark theme compatible
 * - Configurable colors
 */
export default function RadarChart({
    data = {
        deliberation: 0.7,
        priceSensitivity: 0.8,
        cashFlow: 0.5,
        purchaseReadiness: 0.6
    },
    size = 200,
    color = '#667eea'
}) {
    const centerX = size / 2
    const centerY = size / 2
    const radius = (size / 2) - 30 // Leave room for labels

    // Axis labels
    const axes = [
        { key: 'deliberation', label: 'Deliberation', angle: -90 },
        { key: 'priceSensitivity', label: 'Price Sense', angle: 0 },
        { key: 'purchaseReadiness', label: 'Buy Ready', angle: 90 },
        { key: 'cashFlow', label: 'Cash Flow', angle: 180 },
    ]

    // Calculate point positions
    const getPoint = (value, angleDeg) => {
        const angleRad = (angleDeg * Math.PI) / 180
        const r = radius * value
        return {
            x: centerX + r * Math.cos(angleRad),
            y: centerY + r * Math.sin(angleRad)
        }
    }

    // Get label position (slightly outside the chart)
    const getLabelPoint = (angleDeg) => {
        const angleRad = (angleDeg * Math.PI) / 180
        const r = radius + 20
        return {
            x: centerX + r * Math.cos(angleRad),
            y: centerY + r * Math.sin(angleRad)
        }
    }

    // Build path for data polygon
    const dataPoints = axes.map(axis =>
        getPoint(data[axis.key] || 0, axis.angle)
    )
    const pathD = dataPoints.map((p, i) =>
        `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`
    ).join(' ') + ' Z'

    // Build grid circles
    const gridLevels = [0.25, 0.5, 0.75, 1]

    return (
        <svg width={size} height={size} className="overflow-visible">
            {/* Background Grid Circles */}
            {gridLevels.map(level => (
                <circle
                    key={level}
                    cx={centerX}
                    cy={centerY}
                    r={radius * level}
                    fill="none"
                    stroke="rgba(255,255,255,0.1)"
                    strokeWidth="1"
                    strokeDasharray={level === 1 ? "none" : "3,3"}
                />
            ))}

            {/* Axis Lines */}
            {axes.map(axis => {
                const endPoint = getPoint(1, axis.angle)
                return (
                    <line
                        key={axis.key}
                        x1={centerX}
                        y1={centerY}
                        x2={endPoint.x}
                        y2={endPoint.y}
                        stroke="rgba(255,255,255,0.2)"
                        strokeWidth="1"
                    />
                )
            })}

            {/* Data Polygon */}
            <motion.path
                d={pathD}
                fill={`${color}33`} // 20% opacity
                stroke={color}
                strokeWidth="2"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
            />

            {/* Data Points */}
            {dataPoints.map((point, i) => (
                <motion.circle
                    key={i}
                    cx={point.x}
                    cy={point.y}
                    r="4"
                    fill={color}
                    stroke="white"
                    strokeWidth="2"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: 0.3 + i * 0.1, duration: 0.3 }}
                />
            ))}

            {/* Axis Labels */}
            {axes.map(axis => {
                const labelPos = getLabelPoint(axis.angle)
                const textAnchor =
                    axis.angle === 0 ? 'start' :
                        axis.angle === 180 ? 'end' : 'middle'
                const dy =
                    axis.angle === -90 ? '-0.3em' :
                        axis.angle === 90 ? '1em' : '0.35em'

                return (
                    <text
                        key={axis.key}
                        x={labelPos.x}
                        y={labelPos.y}
                        textAnchor={textAnchor}
                        dy={dy}
                        className="text-xs fill-white/60"
                        style={{ fontSize: '10px' }}
                    >
                        {axis.label}
                    </text>
                )
            })}

            {/* Value Labels (on hover or always?) */}
            {dataPoints.map((point, i) => {
                const value = Math.round((data[axes[i].key] || 0) * 100)
                return (
                    <text
                        key={`val-${i}`}
                        x={point.x}
                        y={point.y - 10}
                        textAnchor="middle"
                        className="text-xs fill-white/80 font-medium"
                        style={{ fontSize: '9px' }}
                    >
                        {value}%
                    </text>
                )
            })}
        </svg>
    )
}
