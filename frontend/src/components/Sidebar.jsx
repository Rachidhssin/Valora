import { motion } from 'framer-motion'
import { ShoppingCart, Settings, History, BarChart3, X } from 'lucide-react'
import { useStore } from '../store/useStore'

export default function Sidebar() {
    const { userId, setUserId, budget, setBudget, cart, removeFromCart, clearCart, lastMetrics } = useStore()
    const cartTotal = cart.reduce((sum, item) => sum + item.price, 0)

    return (
        <aside className="fixed left-0 top-0 h-screen w-72 bg-dark-200 border-r border-white/10 p-6 overflow-y-auto">
            {/* Logo */}
            <div className="mb-8">
                <h2 className="text-xl font-bold gradient-text">FinBundle</h2>
                <p className="text-xs text-white/40">Smart Discovery Engine</p>
            </div>

            {/* Settings Section */}
            <section className="mb-8">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-white/60 mb-4">
                    <Settings className="w-4 h-4" />
                    Settings
                </h3>

                <div className="space-y-4">
                    <div>
                        <label className="block text-xs text-white/50 mb-1">User ID</label>
                        <input
                            type="text"
                            value={userId}
                            onChange={(e) => setUserId(e.target.value)}
                            className="w-full px-3 py-2 bg-white/5 border border-white/10 rounded-lg text-sm
                       focus:outline-none focus:border-primary-500"
                        />
                    </div>

                    <div>
                        <label className="block text-xs text-white/50 mb-1">
                            Budget: <span className="text-primary-400 font-semibold">${budget}</span>
                        </label>
                        <input
                            type="range"
                            min="100"
                            max="5000"
                            step="50"
                            value={budget}
                            onChange={(e) => setBudget(Number(e.target.value))}
                            className="w-full accent-primary-500"
                        />
                        <div className="flex justify-between text-xs text-white/30">
                            <span>$100</span>
                            <span>$5000</span>
                        </div>
                    </div>
                </div>
            </section>

            {/* Metrics Section */}
            {lastMetrics && (
                <section className="mb-8">
                    <h3 className="flex items-center gap-2 text-sm font-semibold text-white/60 mb-4">
                        <BarChart3 className="w-4 h-4" />
                        Last Search
                    </h3>

                    <div className="grid grid-cols-2 gap-3">
                        <MetricCard label="Latency" value={`${Math.round(lastMetrics.total_latency_ms)}ms`} />
                        <MetricCard label="Path" value={lastMetrics.path_used?.toUpperCase()} />
                    </div>
                </section>
            )}

            {/* Cart Section */}
            <section className="mb-8">
                <h3 className="flex items-center gap-2 text-sm font-semibold text-white/60 mb-4">
                    <ShoppingCart className="w-4 h-4" />
                    Cart ({cart.length})
                </h3>

                {cart.length > 0 ? (
                    <>
                        <div className="space-y-2 max-h-48 overflow-y-auto">
                            {cart.map((item, i) => (
                                <motion.div
                                    key={item.product_id || i}
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="flex items-center justify-between p-2 bg-white/5 rounded-lg group"
                                >
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-white/80 truncate">{item.name}</p>
                                        <p className="text-xs text-primary-400">${item.price?.toFixed(2)}</p>
                                    </div>
                                    <button
                                        onClick={() => removeFromCart(item.product_id)}
                                        className="p-1 text-white/30 hover:text-red-400 opacity-0 group-hover:opacity-100 transition"
                                    >
                                        <X className="w-4 h-4" />
                                    </button>
                                </motion.div>
                            ))}
                        </div>

                        <div className="mt-4 pt-3 border-t border-white/10">
                            <div className="flex justify-between text-sm">
                                <span className="text-white/60">Total</span>
                                <span className="font-semibold text-primary-400">${cartTotal.toFixed(2)}</span>
                            </div>
                            <button
                                onClick={clearCart}
                                className="w-full mt-3 py-2 text-sm text-white/60 hover:text-white bg-white/5 
                         hover:bg-white/10 rounded-lg transition"
                            >
                                Clear Cart
                            </button>
                        </div>
                    </>
                ) : (
                    <p className="text-sm text-white/40 text-center py-4">Cart is empty</p>
                )}
            </section>

            {/* About */}
            <section className="pt-4 border-t border-white/10">
                <h3 className="text-sm font-semibold text-white/60 mb-3">About</h3>
                <div className="text-xs text-white/40 space-y-1">
                    <p>🧠 AFIG intent reconciliation</p>
                    <p>⚡ Three-path routing</p>
                    <p>🤖 AI affordability agent</p>
                    <p>🎯 Bundle optimization</p>
                </div>
            </section>
        </aside>
    )
}

function MetricCard({ label, value }) {
    return (
        <div className="p-3 bg-white/5 rounded-lg">
            <p className="text-xs text-white/50">{label}</p>
            <p className="text-lg font-semibold text-white">{value}</p>
        </div>
    )
}
