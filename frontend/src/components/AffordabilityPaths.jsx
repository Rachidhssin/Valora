import { motion, AnimatePresence } from 'framer-motion'
import { 
    Lightbulb, 
    ShoppingCart, 
    Clock, 
    CreditCard, 
    RefreshCw, 
    ArrowLeftRight,
    AlertCircle,
    CheckCircle,
    ChevronRight,
    Sparkles
} from 'lucide-react'

/**
 * AffordabilityPaths - Display agent-recommended paths to afford products
 * 
 * Shows creative solutions when user is over budget:
 * - Cart removals
 * - Save & wait
 * - Installment plans
 * - Refurbished alternatives
 * - Bundle swaps
 */

// Map path types to icons and colors
const pathConfig = {
    cart_removal: {
        icon: ShoppingCart,
        color: 'text-amber-400',
        bg: 'bg-amber-500/10',
        border: 'border-amber-500/30',
        label: 'Remove Items'
    },
    save_and_wait: {
        icon: Clock,
        color: 'text-blue-400',
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/30',
        label: 'Save & Wait'
    },
    installment: {
        icon: CreditCard,
        color: 'text-purple-400',
        bg: 'bg-purple-500/10',
        border: 'border-purple-500/30',
        label: 'Installments'
    },
    refurbished: {
        icon: RefreshCw,
        color: 'text-green-400',
        bg: 'bg-green-500/10',
        border: 'border-green-500/30',
        label: 'Refurbished'
    },
    bundle_swap: {
        icon: ArrowLeftRight,
        color: 'text-cyan-400',
        bg: 'bg-cyan-500/10',
        border: 'border-cyan-500/30',
        label: 'Swap Items'
    }
}

function PathCard({ path, index, onApply }) {
    const config = pathConfig[path.path_type] || {
        icon: Lightbulb,
        color: 'text-primary-400',
        bg: 'bg-primary-500/10',
        border: 'border-primary-500/30',
        label: path.path_type
    }

    const Icon = config.icon

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className={`p-4 rounded-xl border ${config.border} ${config.bg} 
                       hover:border-opacity-60 transition-all cursor-pointer group`}
            onClick={() => onApply?.(path)}
        >
            {/* Header */}
            <div className="flex items-start gap-3">
                <div className={`p-2 rounded-lg ${config.bg}`}>
                    <Icon className={`w-5 h-5 ${config.color}`} />
                </div>
                
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <span className={`text-xs font-medium uppercase tracking-wide ${config.color}`}>
                            {config.label}
                        </span>
                        {path.viable && (
                            <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                        )}
                    </div>
                    
                    <h4 className="text-sm font-medium text-white mt-1 line-clamp-2">
                        {path.summary}
                    </h4>
                </div>

                <ChevronRight className="w-5 h-5 text-white/30 group-hover:text-white/60 
                                        group-hover:translate-x-1 transition-all flex-shrink-0" />
            </div>

            {/* Details */}
            <div className="mt-3 space-y-2">
                {/* Action */}
                <div className="flex items-start gap-2 text-xs">
                    <span className="text-white/40 flex-shrink-0">Action:</span>
                    <span className="text-white/70">{path.action}</span>
                </div>

                {/* Trade-off */}
                {path.trade_off && path.trade_off !== 'N/A' && (
                    <div className="flex items-start gap-2 text-xs">
                        <span className="text-white/40 flex-shrink-0">Trade-off:</span>
                        <span className="text-white/60">{path.trade_off}</span>
                    </div>
                )}

                {/* Savings */}
                {path.savings > 0 && (
                    <div className="flex items-center gap-2 mt-2">
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 
                                       text-xs font-medium rounded-full">
                            Save ${path.savings.toFixed(0)}
                        </span>
                    </div>
                )}

                {/* Weeks (for save_and_wait) */}
                {path.weeks && (
                    <div className="flex items-center gap-2 mt-2">
                        <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 
                                       text-xs font-medium rounded-full">
                            {path.weeks} weeks
                        </span>
                    </div>
                )}

                {/* Plan details (for installment) */}
                {path.plan && (
                    <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className="px-2 py-0.5 bg-purple-500/20 text-purple-400 
                                       text-xs font-medium rounded-full">
                            ${path.plan.monthly_payment}/mo
                        </span>
                        <span className="px-2 py-0.5 bg-purple-500/10 text-purple-300 
                                       text-xs rounded-full">
                            {path.plan.months} months
                        </span>
                    </div>
                )}

                {/* Product (for refurbished) */}
                {path.product && (
                    <div className="mt-2 p-2 bg-white/5 rounded-lg">
                        <p className="text-xs text-white/80 truncate">{path.product.name}</p>
                        <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-green-400 font-medium">
                                ${path.product.price?.toFixed(0)}
                            </span>
                            {path.product.condition && (
                                <span className="text-xs text-white/40 capitalize">
                                    {path.product.condition}
                                </span>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </motion.div>
    )
}

export default function AffordabilityPaths({ agentPaths, onApplyPath }) {
    if (!agentPaths || agentPaths.status === 'no_gap' || agentPaths.status === 'affordable') {
        return null
    }

    const paths = agentPaths.paths || []
    const gap = agentPaths.gap || 0

    if (paths.length === 0 && agentPaths.status !== 'paths_found') {
        return null
    }

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden"
        >
            {/* Header */}
            <div className="p-4 border-b border-white/10">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-primary-500/20 rounded-xl">
                        <Sparkles className="w-5 h-5 text-primary-400" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-white flex items-center gap-2">
                            Budget Pathfinder
                            {gap > 0 && (
                                <span className="text-xs text-red-400 bg-red-500/20 
                                               px-2 py-0.5 rounded-full">
                                    ${gap.toFixed(0)} over budget
                                </span>
                            )}
                        </h3>
                        <p className="text-xs text-white/50 mt-0.5">
                            AI-powered ways to afford your items
                        </p>
                    </div>
                </div>
            </div>

            {/* Paths */}
            <div className="p-4 space-y-3">
                {paths.length > 0 ? (
                    <AnimatePresence>
                        {paths.map((path, index) => (
                            <PathCard
                                key={`${path.path_type}-${index}`}
                                path={path}
                                index={index}
                                onApply={onApplyPath}
                            />
                        ))}
                    </AnimatePresence>
                ) : (
                    <div className="text-center py-6">
                        <AlertCircle className="w-8 h-8 text-white/30 mx-auto mb-2" />
                        <p className="text-sm text-white/50">
                            No affordability paths found
                        </p>
                        <p className="text-xs text-white/30 mt-1">
                            Try adjusting your budget or cart items
                        </p>
                    </div>
                )}
            </div>

            {/* Agent Stats (Optional) */}
            {agentPaths.agent_steps && (
                <div className="px-4 py-2 border-t border-white/5 flex items-center 
                               justify-between text-xs text-white/30">
                    <span>Agent analyzed in {agentPaths.agent_steps} steps</span>
                    {agentPaths.token_usage?.total_tokens && (
                        <span>{agentPaths.token_usage.total_tokens} tokens</span>
                    )}
                </div>
            )}
        </motion.div>
    )
}
