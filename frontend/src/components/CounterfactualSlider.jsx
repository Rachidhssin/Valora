import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { TrendingUp, TrendingDown, ArrowRight, Sparkles, X } from 'lucide-react'
import { useStore } from '../store/useStore'

/**
 * CounterfactualSlider - Interactive "What if I had more/less budget?" analysis
 * 
 * Features:
 * - Slider: -$500 ↔ +$500
 * - Shows upgrade/downgrade paths
 * - Quality score delta
 * - Specific trade-offs explained
 */
export default function CounterfactualSlider({
    isOpen,
    onClose,
    currentQuality = 7.5,
    onApply
}) {
    const { budget, cart } = useStore()
    const cartTotal = cart.reduce((sum, item) => sum + (item.price || 0), 0)

    const [delta, setDelta] = useState(0)
    const [recommendations, setRecommendations] = useState([])

    const newBudget = budget + delta
    const qualityDelta = calculateQualityChange(delta, cartTotal, budget)
    const newQuality = Math.min(10, Math.max(0, currentQuality + qualityDelta))

    // Simulate recommendations when delta changes
    useEffect(() => {
        if (delta === 0) {
            setRecommendations([])
            return
        }

        // Simulated recommendations based on budget change
        if (delta > 0) {
            setRecommendations([
                {
                    type: 'upgrade',
                    text: 'Upgrade from 1080p to 1440p monitor',
                    impact: '+0.4 quality'
                },
                {
                    type: 'upgrade',
                    text: 'Add extended warranty coverage',
                    impact: '+0.2 quality'
                },
                delta >= 200 && {
                    type: 'upgrade',
                    text: 'Include premium accessories bundle',
                    impact: '+0.6 quality'
                },
            ].filter(Boolean))
        } else {
            setRecommendations([
                {
                    type: 'downgrade',
                    text: 'Switch to previous-gen model',
                    impact: '-0.3 quality'
                },
                {
                    type: 'downgrade',
                    text: 'Remove extended warranty',
                    impact: '-0.2 quality'
                },
                delta <= -200 && {
                    type: 'alternative',
                    text: 'Consider refurbished option',
                    impact: 'Same features, certified'
                },
            ].filter(Boolean))
        }
    }, [delta])

    if (!isOpen) return null

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 
                           flex items-center justify-center p-4"
                onClick={onClose}
            >
                <motion.div
                    initial={{ scale: 0.9, y: 20 }}
                    animate={{ scale: 1, y: 0 }}
                    exit={{ scale: 0.9, y: 20 }}
                    onClick={e => e.stopPropagation()}
                    className="w-full max-w-lg bg-dark-100 border border-white/10 
                               rounded-2xl overflow-hidden shadow-2xl"
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 border-b border-white/10">
                        <div className="flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-primary-400" />
                            <h2 className="font-semibold text-white">
                                Budget What-If Analysis
                            </h2>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1.5 hover:bg-white/10 rounded-lg transition-colors"
                        >
                            <X className="w-5 h-5 text-white/60" />
                        </button>
                    </div>

                    {/* Content */}
                    <div className="p-6 space-y-6">
                        {/* Current vs New Budget */}
                        <div className="flex items-center justify-center gap-4">
                            <div className="text-center">
                                <p className="text-xs text-white/50 mb-1">Current</p>
                                <p className="text-2xl font-bold text-white/60">
                                    ${budget}
                                </p>
                            </div>
                            <ArrowRight className="w-6 h-6 text-white/30" />
                            <div className="text-center">
                                <p className="text-xs text-white/50 mb-1">Adjusted</p>
                                <p className={`text-2xl font-bold ${delta > 0 ? 'text-emerald-400' :
                                        delta < 0 ? 'text-amber-400' : 'text-white'
                                    }`}>
                                    ${newBudget}
                                </p>
                            </div>
                        </div>

                        {/* Slider */}
                        <div className="space-y-3">
                            <div className="flex items-center justify-between text-sm">
                                <span className="text-white/50">-$500</span>
                                <span className={`font-semibold ${delta > 0 ? 'text-emerald-400' :
                                        delta < 0 ? 'text-amber-400' : 'text-white/70'
                                    }`}>
                                    {delta >= 0 ? '+' : ''}{delta}
                                </span>
                                <span className="text-white/50">+$500</span>
                            </div>

                            <input
                                type="range"
                                min="-500"
                                max="500"
                                step="50"
                                value={delta}
                                onChange={(e) => setDelta(Number(e.target.value))}
                                className="w-full h-2 bg-white/10 rounded-lg appearance-none 
                                           cursor-pointer accent-primary-500
                                           [&::-webkit-slider-thumb]:w-5 
                                           [&::-webkit-slider-thumb]:h-5 
                                           [&::-webkit-slider-thumb]:rounded-full
                                           [&::-webkit-slider-thumb]:bg-primary-500
                                           [&::-webkit-slider-thumb]:shadow-lg"
                            />

                            {/* Quick Select */}
                            <div className="flex justify-center gap-2">
                                {[-200, -100, 0, 100, 200].map(val => (
                                    <button
                                        key={val}
                                        onClick={() => setDelta(val)}
                                        className={`px-3 py-1 text-xs rounded-full transition-all ${delta === val
                                                ? 'bg-primary-500 text-white'
                                                : 'bg-white/5 text-white/60 hover:bg-white/10'
                                            }`}
                                    >
                                        {val >= 0 ? '+' : ''}{val}
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Quality Impact */}
                        <div className="p-4 bg-white/5 rounded-xl space-y-3">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <Sparkles className="w-4 h-4 text-amber-400" />
                                    <span className="text-sm text-white/70">Quality Score</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-white/60">{currentQuality.toFixed(1)}</span>
                                    <ArrowRight className="w-4 h-4 text-white/30" />
                                    <span className={`font-bold ${qualityDelta > 0 ? 'text-emerald-400' :
                                            qualityDelta < 0 ? 'text-amber-400' : 'text-white'
                                        }`}>
                                        {newQuality.toFixed(1)}
                                    </span>
                                    {qualityDelta !== 0 && (
                                        <span className={`text-xs ${qualityDelta > 0 ? 'text-emerald-400' : 'text-amber-400'
                                            }`}>
                                            ({qualityDelta > 0 ? '+' : ''}{qualityDelta.toFixed(1)})
                                        </span>
                                    )}
                                </div>
                            </div>

                            {/* Quality Bar */}
                            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                <motion.div
                                    className={`h-full rounded-full ${newQuality >= 8 ? 'bg-emerald-500' :
                                            newQuality >= 6 ? 'bg-amber-500' : 'bg-orange-500'
                                        }`}
                                    animate={{ width: `${newQuality * 10}%` }}
                                    transition={{ duration: 0.3 }}
                                />
                            </div>
                        </div>

                        {/* Recommendations */}
                        {recommendations.length > 0 && (
                            <div className="space-y-2">
                                <h4 className="text-sm font-medium text-white/70">
                                    {delta > 0 ? '✨ Upgrade Paths' : '💡 Alternatives'}
                                </h4>

                                <div className="space-y-2">
                                    {recommendations.map((rec, i) => (
                                        <motion.div
                                            key={i}
                                            initial={{ opacity: 0, x: -10 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: i * 0.1 }}
                                            className="flex items-center gap-3 p-3 bg-white/5 rounded-lg"
                                        >
                                            {rec.type === 'upgrade' ? (
                                                <TrendingUp className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                                            ) : rec.type === 'downgrade' ? (
                                                <TrendingDown className="w-4 h-4 text-amber-400 flex-shrink-0" />
                                            ) : (
                                                <ArrowRight className="w-4 h-4 text-primary-400 flex-shrink-0" />
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-white/80">{rec.text}</p>
                                            </div>
                                            <span className={`text-xs font-medium ${rec.type === 'upgrade' ? 'text-emerald-400' :
                                                    rec.type === 'downgrade' ? 'text-amber-400' :
                                                        'text-primary-400'
                                                }`}>
                                                {rec.impact}
                                            </span>
                                        </motion.div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Footer */}
                    <div className="flex gap-3 p-4 border-t border-white/10">
                        <button
                            onClick={onClose}
                            className="flex-1 py-2.5 bg-white/5 hover:bg-white/10 
                                       text-white/70 rounded-xl transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={() => onApply?.(newBudget)}
                            disabled={delta === 0}
                            className="flex-1 py-2.5 bg-primary-500 hover:bg-primary-600 
                                       text-white font-medium rounded-xl transition-colors
                                       disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Apply ${newBudget} Budget
                        </button>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}

/**
 * Calculate quality change based on budget delta
 */
function calculateQualityChange(delta, cartTotal, budget) {
    if (delta === 0) return 0

    // Simplified quality impact calculation
    const budgetRatio = delta / budget
    const qualityImpact = budgetRatio * 3 // Scale factor

    return Math.round(qualityImpact * 10) / 10
}
