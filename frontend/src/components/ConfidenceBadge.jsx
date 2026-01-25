import { motion } from 'framer-motion'

/**
 * ConfidenceBadge - Match percentage with color-coded indicator
 * 
 * Features:
 * - Color gradient based on score
 * - Tooltip with reasoning
 * - Compact and inline-friendly
 */
export default function ConfidenceBadge({ score, showLabel = true, size = 'md' }) {
    const percentage = Math.round(score * 100)

    // Color based on percentage
    const getColors = () => {
        if (percentage >= 80) return {
            bg: 'bg-emerald-500/20',
            text: 'text-emerald-400',
            border: 'border-emerald-500/30'
        }
        if (percentage >= 60) return {
            bg: 'bg-amber-500/20',
            text: 'text-amber-400',
            border: 'border-amber-500/30'
        }
        return {
            bg: 'bg-orange-500/20',
            text: 'text-orange-400',
            border: 'border-orange-500/30'
        }
    }

    const colors = getColors()

    const sizes = {
        sm: 'px-1.5 py-0.5 text-xs',
        md: 'px-2 py-1 text-xs',
        lg: 'px-3 py-1.5 text-sm'
    }

    return (
        <motion.div
            className={`inline-flex items-center gap-1 ${sizes[size]} ${colors.bg} ${colors.text} 
                       border ${colors.border} rounded-full font-medium`}
            whileHover={{ scale: 1.05 }}
            title={`${percentage}% confidence match`}
        >
            <span className="font-semibold">{percentage}%</span>
            {showLabel && <span className="opacity-70">match</span>}
        </motion.div>
    )
}

/**
 * Budget Fit Badge - Shows if price fits the budget
 */
export function BudgetFitBadge({ price, budget }) {
    const ratio = price / budget

    if (ratio <= 0.3) {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-emerald-500/20 
                           text-emerald-400 text-xs rounded-full">
                💰 Great value
            </span>
        )
    }
    if (ratio <= 0.6) {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-primary-500/20 
                           text-primary-400 text-xs rounded-full">
                ✓ In budget
            </span>
        )
    }
    if (ratio <= 0.9) {
        return (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-amber-500/20 
                           text-amber-400 text-xs rounded-full">
                ⚠ Tight fit
            </span>
        )
    }
    return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-red-500/20 
                       text-red-400 text-xs rounded-full">
            ⛔ Over budget
        </span>
    )
}
