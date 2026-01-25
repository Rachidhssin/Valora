import { motion } from 'framer-motion'

/**
 * BudgetBar - Visual budget progress indicator
 * 
 * Features:
 * - Color-coded progress (green/yellow/red)
 * - Animated transitions
 * - Shows used/remaining budget
 */
export default function BudgetBar({ used, total, showLabels = true, size = 'md' }) {
    const percentage = Math.min(100, (used / total) * 100)
    const remaining = total - used

    // Color based on percentage
    const getColor = () => {
        if (percentage <= 60) return 'from-emerald-500 to-emerald-400'
        if (percentage <= 85) return 'from-amber-500 to-amber-400'
        return 'from-red-500 to-red-400'
    }

    const getTextColor = () => {
        if (percentage <= 60) return 'text-emerald-400'
        if (percentage <= 85) return 'text-amber-400'
        return 'text-red-400'
    }

    const heights = {
        sm: 'h-1.5',
        md: 'h-2.5',
        lg: 'h-4'
    }

    return (
        <div className="space-y-2">
            {/* Labels */}
            {showLabels && (
                <div className="flex justify-between items-center text-sm">
                    <span className="text-white/60">
                        Used: <span className={getTextColor()}>${used.toFixed(2)}</span>
                    </span>
                    <span className="text-white/60">
                        Remaining: <span className="text-white/80">${remaining.toFixed(2)}</span>
                    </span>
                </div>
            )}

            {/* Progress Bar Container */}
            <div className={`w-full ${heights[size]} bg-white/10 rounded-full overflow-hidden`}>
                <motion.div
                    className={`h-full bg-gradient-to-r ${getColor()} rounded-full`}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                />
            </div>

            {/* Percentage Label */}
            {showLabels && (
                <div className="flex justify-between items-center">
                    <span className={`text-xs font-medium ${getTextColor()}`}>
                        {percentage.toFixed(0)}% used
                    </span>
                    <span className="text-xs text-white/40">
                        of ${total} budget
                    </span>
                </div>
            )}
        </div>
    )
}

/**
 * Mini version for inline use
 */
export function BudgetBarMini({ used, total }) {
    const percentage = Math.min(100, (used / total) * 100)

    const getColor = () => {
        if (percentage <= 60) return 'bg-emerald-500'
        if (percentage <= 85) return 'bg-amber-500'
        return 'bg-red-500'
    }

    return (
        <div className="flex items-center gap-2">
            <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                    className={`h-full ${getColor()} rounded-full`}
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.3 }}
                />
            </div>
            <span className="text-xs text-white/50">{percentage.toFixed(0)}%</span>
        </div>
    )
}
