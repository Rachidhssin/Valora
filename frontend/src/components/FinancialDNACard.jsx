import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronDown, ChevronUp, Shield, HelpCircle, User } from 'lucide-react'
import RadarChart from './RadarChart'
import { useStore } from '../store/useStore'

/**
 * FinancialDNACard - User archetype visualization with radar chart
 * 
 * Features:
 * - Collapsible card
 * - 4-axis radar chart
 * - Archetype badge
 * - Confidence meter
 * - Privacy badge
 * - Educational tooltip
 */

// Archetype definitions
const ARCHETYPES = {
    value_hunter: {
        name: 'Value Hunter',
        emoji: '🎯',
        color: 'text-emerald-400',
        bgColor: 'bg-emerald-500/20',
        description: 'Seeks the best bang for buck'
    },
    brand_loyalist: {
        name: 'Brand Loyalist',
        emoji: '🏆',
        color: 'text-amber-400',
        bgColor: 'bg-amber-500/20',
        description: 'Trusts established brands'
    },
    impulse_buyer: {
        name: 'Impulse Buyer',
        emoji: '⚡',
        color: 'text-pink-400',
        bgColor: 'bg-pink-500/20',
        description: 'Quick decisions, trend-driven'
    },
    planner: {
        name: 'Planner',
        emoji: '📋',
        color: 'text-cyan-400',
        bgColor: 'bg-cyan-500/20',
        description: 'Researches thoroughly'
    },
    deal_seeker: {
        name: 'Deal Seeker',
        emoji: '🏷️',
        color: 'text-orange-400',
        bgColor: 'bg-orange-500/20',
        description: 'Lives for discounts'
    },
    default: {
        name: 'Balanced',
        emoji: '⚖️',
        color: 'text-primary-400',
        bgColor: 'bg-primary-500/20',
        description: 'Well-rounded approach'
    }
}

export default function FinancialDNACard() {
    const [isExpanded, setIsExpanded] = useState(true)
    const [showPrivacyInfo, setShowPrivacyInfo] = useState(false)

    const { financialDNA } = useStore()

    // Default DNA if not set
    const dna = financialDNA || {
        archetype: 'value_hunter',
        confidence: 0.72,
        traits: {
            deliberation: 0.65,
            priceSensitivity: 0.85,
            cashFlow: 0.55,
            purchaseReadiness: 0.70
        }
    }

    const archetype = ARCHETYPES[dna.archetype] || ARCHETYPES.default
    const confidencePercent = Math.round(dna.confidence * 100)

    return (
        <motion.div
            className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            layout
        >
            {/* Header - Always Visible */}
            <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 ${archetype.bgColor} rounded-xl 
                                   flex items-center justify-center text-lg`}>
                        {archetype.emoji}
                    </div>
                    <div className="text-left">
                        <h3 className="text-sm font-semibold text-white/90">
                            Financial DNA
                        </h3>
                        <p className={`text-xs ${archetype.color}`}>
                            {archetype.name}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2">
                    {/* Confidence Pill */}
                    <span className="px-2 py-1 bg-primary-500/20 text-primary-400 
                                   text-xs rounded-full font-medium">
                        {confidencePercent}% confident
                    </span>

                    {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-white/40" />
                    ) : (
                        <ChevronDown className="w-5 h-5 text-white/40" />
                    )}
                </div>
            </button>

            {/* Expanded Content */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.3 }}
                        className="overflow-hidden"
                    >
                        <div className="px-4 pb-4 space-y-4">
                            {/* Radar Chart */}
                            <div className="flex justify-center py-2">
                                <RadarChart
                                    data={dna.traits}
                                    size={180}
                                    color="#667eea"
                                />
                            </div>

                            {/* Archetype Description */}
                            <div className={`p-3 ${archetype.bgColor} rounded-xl`}>
                                <p className={`text-sm ${archetype.color}`}>
                                    <span className="font-medium">{archetype.name}:</span>{' '}
                                    {archetype.description}
                                </p>
                            </div>

                            {/* Trait Bars */}
                            <div className="space-y-2">
                                {Object.entries(dna.traits).map(([key, value]) => (
                                    <TraitBar
                                        key={key}
                                        label={formatTraitLabel(key)}
                                        value={value}
                                    />
                                ))}
                            </div>

                            {/* Footer - Privacy & Help */}
                            <div className="flex items-center justify-between pt-2 border-t border-white/10">
                                {/* Privacy Badge */}
                                <button
                                    onClick={() => setShowPrivacyInfo(!showPrivacyInfo)}
                                    className="flex items-center gap-1.5 text-xs text-white/50 
                                               hover:text-white/70 transition-colors"
                                >
                                    <Shield className="w-3.5 h-3.5" />
                                    <span>Encrypted & Anonymous</span>
                                </button>

                                {/* Help Button */}
                                <button
                                    className="flex items-center gap-1 text-xs text-white/50 
                                               hover:text-white/70 transition-colors"
                                    title="How we infer your financial profile"
                                >
                                    <HelpCircle className="w-3.5 h-3.5" />
                                    <span>How it works</span>
                                </button>
                            </div>

                            {/* Privacy Info Tooltip */}
                            <AnimatePresence>
                                {showPrivacyInfo && (
                                    <motion.div
                                        initial={{ opacity: 0, height: 0 }}
                                        animate={{ opacity: 1, height: 'auto' }}
                                        exit={{ opacity: 0, height: 0 }}
                                        className="p-3 bg-emerald-500/10 border border-emerald-500/20 
                                                   rounded-xl text-xs text-emerald-300/80"
                                    >
                                        <p className="flex items-start gap-2">
                                            <Shield className="w-4 h-4 mt-0.5 flex-shrink-0" />
                                            <span>
                                                Your financial DNA is inferred from browsing patterns only.
                                                No personal financial data is collected. All data is encrypted
                                                and stored anonymously.
                                            </span>
                                        </p>
                                    </motion.div>
                                )}
                            </AnimatePresence>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}

function TraitBar({ label, value }) {
    const percentage = Math.round(value * 100)

    return (
        <div className="space-y-1">
            <div className="flex justify-between text-xs">
                <span className="text-white/60">{label}</span>
                <span className="text-white/80 font-medium">{percentage}%</span>
            </div>
            <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                <motion.div
                    className="h-full bg-gradient-to-r from-primary-500 to-primary-400 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: `${percentage}%` }}
                    transition={{ duration: 0.5, delay: 0.1 }}
                />
            </div>
        </div>
    )
}

function formatTraitLabel(key) {
    const labels = {
        deliberation: 'Deliberation',
        priceSensitivity: 'Price Sensitivity',
        cashFlow: 'Cash Flow Awareness',
        purchaseReadiness: 'Purchase Readiness'
    }
    return labels[key] || key
}
