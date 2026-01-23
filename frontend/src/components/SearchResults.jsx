import { useEffect } from 'react'
import { motion } from 'framer-motion'
import { Package, Zap, Brain, Target, Sparkles, ShoppingCart, Clock, AlertCircle } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function SearchResults({ result }) {
    const { setLastMetrics } = useStore()

    // Store metrics
    // Store metrics
    useEffect(() => {
        if (result?.metrics) {
            setLastMetrics(result.metrics)
        }
    }, [result, setLastMetrics])

    const path = result.path
    const metrics = result.metrics || {}

    return (
        <div className="space-y-6">
            {/* Success Banner */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between p-4 glass"
            >
                <div className="flex items-center gap-3">
                    <span className="text-green-400 text-lg">✅</span>
                    <span className="text-white/80">
                        Found results via <PathBadge path={path} /> path in{' '}
                        <span className="font-semibold text-primary-400">{Math.round(metrics.total_latency_ms)}ms</span>
                    </span>
                </div>
                <span className="text-sm text-white/50">{metrics.route_reason}</span>
            </motion.div>

            {/* Results based on path */}
            {path === 'fast' && <FastPathResults results={result.results} />}
            {path === 'smart' && <SmartPathResults results={result.results} />}
            {path === 'deep' && (
                <DeepPathResults
                    bundle={result.bundle}
                    agentPaths={result.agent_paths}
                    explanations={result.explanations}
                    bundleExplanation={result.bundle_explanation}
                />
            )}
        </div>
    )
}

function PathBadge({ path }) {
    const styles = {
        fast: 'badge-fast',
        smart: 'badge-smart',
        deep: 'badge-deep'
    }

    const icons = {
        fast: <Zap className="w-3 h-3" />,
        smart: <Brain className="w-3 h-3" />,
        deep: <Target className="w-3 h-3" />
    }

    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${styles[path]}`}>
            {icons[path]}
            {path.toUpperCase()}
        </span>
    )
}

function FastPathResults({ results = [] }) {
    return (
        <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                <Zap className="w-5 h-5 text-green-400" />
                Quick Results
            </h2>
            <ProductGrid products={results} />
        </div>
    )
}

function SmartPathResults({ results = [] }) {
    return (
        <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                <Brain className="w-5 h-5 text-blue-400" />
                Smart Recommendations
            </h2>
            <ProductGrid products={results} />
        </div>
    )
}

function DeepPathResults({ bundle, agentPaths, explanations, bundleExplanation }) {
    const bundleItems = bundle?.bundle || []

    return (
        <div className="space-y-8">
            {/* Bundle Header */}
            <div>
                <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                    <Target className="w-5 h-5 text-purple-400" />
                    Optimized Bundle
                </h2>

                {/* Bundle Stats */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <StatCard
                        label="Total"
                        value={`$${bundle?.total_price?.toFixed(2) || '0'}`}
                        icon={<Package className="w-4 h-4" />}
                    />
                    <StatCard
                        label="Budget Used"
                        value={`${((bundle?.budget_used || 0) * 100).toFixed(0)}%`}
                        icon={<Target className="w-4 h-4" />}
                        highlight={bundle?.budget_used > 1}
                    />
                    <StatCard
                        label="Items"
                        value={bundleItems.length}
                        icon={<ShoppingCart className="w-4 h-4" />}
                    />
                    <StatCard
                        label="Method"
                        value={bundle?.method?.toUpperCase() || 'N/A'}
                        icon={<Sparkles className="w-4 h-4" />}
                    />
                </div>
            </div>

            {/* Bundle Items */}
            <div className="space-y-3">
                {bundleItems.map((item, i) => (
                    <BundleItem
                        key={item.id || i}
                        item={item}
                        explanation={explanations?.find(e => e.product_id === item.id)?.explanation}
                    />
                ))}
            </div>

            {/* Bundle Explanation */}
            {bundleExplanation && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="p-4 bg-primary-500/10 border border-primary-500/30 rounded-xl"
                >
                    <h3 className="flex items-center gap-2 font-semibold mb-2">
                        <Sparkles className="w-4 h-4 text-primary-400" />
                        Why This Bundle
                    </h3>
                    <p className="text-white/80">{bundleExplanation}</p>
                </motion.div>
            )}

            {/* Agent Paths */}
            {agentPaths?.status === 'paths_found' && agentPaths.paths?.length > 0 && (
                <AgentPathsSection paths={agentPaths.paths} gap={agentPaths.gap} />
            )}
        </div>
    )
}

function ProductGrid({ products = [] }) {
    const { addToCart } = useStore()

    if (products.length === 0) {
        return (
            <div className="text-center py-8 text-white/50">
                No products found. Try adjusting your search or budget.
            </div>
        )
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.slice(0, 9).map((product, i) => (
                <motion.div
                    key={product.product_id || i}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.05 }}
                    className="glass p-4 card-hover"
                >
                    <h3 className="font-semibold text-white truncate">{product.name}</h3>
                    <p className="text-sm text-white/50">
                        {product.category} • {product.brand || 'Generic'}
                    </p>

                    <div className="flex items-center justify-between mt-3">
                        <div>
                            <span className="text-lg font-bold text-primary-400">${product.price}</span>
                            <div className="flex items-center gap-2 text-sm text-white/60">
                                <span>⭐ {product.rating}/5</span>
                                {(product.utility !== undefined && product.utility > 0) && (
                                    <span className="text-xs px-1.5 py-0.5 bg-white/10 rounded">
                                        Score: {product.utility?.toFixed(2)}
                                    </span>
                                )}
                            </div>
                        </div>
                        <button
                            onClick={() => addToCart(product)}
                            className="btn-secondary text-sm"
                        >
                            Add
                        </button>
                    </div>
                </motion.div>
            ))}
        </div>
    )
}

function StatCard({ label, value, icon, highlight = false }) {
    return (
        <div className={`p-4 rounded-xl ${highlight ? 'bg-red-500/20 border border-red-500/30' : 'glass'}`}>
            <div className="flex items-center gap-2 text-white/50 text-sm mb-1">
                {icon}
                {label}
            </div>
            <p className="text-xl font-bold">{value}</p>
        </div>
    )
}

function BundleItem({ item, explanation }) {
    const { addToCart } = useStore()

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass p-4"
        >
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <h4 className="font-semibold">{item.name}</h4>
                    <p className="text-sm text-white/50">{item.category}</p>
                    {explanation && (
                        <p className="mt-2 text-sm text-primary-300 bg-primary-500/10 p-2 rounded-lg">
                            💡 {explanation}
                        </p>
                    )}
                </div>
                <div className="text-right">
                    <p className="text-lg font-bold text-primary-400">${item.price}</p>
                    <p className="text-xs text-white/50">Utility: {item.utility?.toFixed(3)}</p>
                    <button
                        onClick={() => addToCart({ product_id: item.id, ...item })}
                        className="mt-2 btn-secondary text-xs py-1"
                    >
                        Add to Cart
                    </button>
                </div>
            </div>
        </motion.div>
    )
}

function AgentPathsSection({ paths, gap }) {
    return (
        <div className="mt-8">
            <h3 className="flex items-center gap-2 text-lg font-semibold mb-4">
                <Sparkles className="w-5 h-5 text-purple-400" />
                AI Affordability Assistant
            </h3>

            {gap > 0 && (
                <div className="flex items-center gap-2 p-3 mb-4 bg-yellow-500/20 border border-yellow-500/30 rounded-lg">
                    <AlertCircle className="w-5 h-5 text-yellow-400" />
                    <span className="text-yellow-200">
                        Budget gap detected: <strong>${gap.toFixed(2)}</strong> over budget
                    </span>
                </div>
            )}

            <div className="space-y-3">
                {paths.map((path, i) => (
                    <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.1 }}
                        className="agent-path-card"
                    >
                        <div className="flex items-start justify-between">
                            <div>
                                <span className="inline-block px-2 py-0.5 bg-purple-500/30 text-purple-300 text-xs rounded-full mb-2">
                                    Option {i + 1}: {path.path_type?.replace('_', ' ').toUpperCase()}
                                </span>
                                <p className="font-medium text-white">{path.summary}</p>
                                <p className="mt-1 text-sm text-white/70">
                                    <strong>Action:</strong> {path.action}
                                </p>
                                <p className="text-sm text-white/50 italic">
                                    Trade-off: {path.trade_off}
                                </p>
                            </div>
                            {path.savings > 0 && (
                                <div className="text-right">
                                    <p className="text-xs text-white/50">Potential Savings</p>
                                    <p className="text-lg font-bold text-green-400">${path.savings.toFixed(2)}</p>
                                </div>
                            )}
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    )
}
