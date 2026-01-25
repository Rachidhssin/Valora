import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { ShoppingCart, X, Sparkles, Zap, TrendingUp, MinusCircle, PlusCircle } from 'lucide-react'
import { useStore } from '../store/useStore'
import BudgetBar from './BudgetBar'

/**
 * BundleCart - Enhanced cart with bundle optimization features
 * 
 * Features:
 * - Product thumbnails with remove
 * - Budget bar integration
 * - Quality score meter
 * - "Optimize Bundle" button
 * - Counterfactual slider trigger
 */
export default function BundleCart({ onOptimize, onCounterfactual }) {
    const [isOptimizing, setIsOptimizing] = useState(false)
    const { cart, removeFromCart, clearCart, budget } = useStore()

    const cartTotal = cart.reduce((sum, item) => sum + (item.price || 0), 0)
    const qualityScore = calculateQualityScore(cart)

    const handleOptimize = async () => {
        setIsOptimizing(true)
        await onOptimize?.()
        setIsOptimizing(false)
    }

    return (
        <div className="bg-white/5 border border-white/10 rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/10">
                <div className="flex items-center gap-2">
                    <ShoppingCart className="w-5 h-5 text-primary-400" />
                    <h3 className="font-semibold text-white">Your Bundle</h3>
                    <span className="px-2 py-0.5 bg-primary-500/20 text-primary-400 
                                   text-xs rounded-full">
                        {cart.length} items
                    </span>
                </div>

                {cart.length > 0 && (
                    <button
                        onClick={clearCart}
                        className="text-xs text-white/40 hover:text-red-400 transition-colors"
                    >
                        Clear all
                    </button>
                )}
            </div>

            {/* Cart Items */}
            <div className="p-4 space-y-3 max-h-64 overflow-y-auto">
                <AnimatePresence>
                    {cart.length > 0 ? (
                        cart.map((item, index) => (
                            <motion.div
                                key={item.product_id || index}
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20, height: 0 }}
                                className="flex items-center gap-3 p-2 bg-white/5 rounded-xl group"
                            >
                                {/* Thumbnail */}
                                <div className="w-12 h-12 bg-white/10 rounded-lg overflow-hidden flex-shrink-0">
                                    {item.image_url ? (
                                        <img
                                            src={item.image_url}
                                            alt={item.name}
                                            className="w-full h-full object-cover"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-lg">
                                            📦
                                        </div>
                                    )}
                                </div>

                                {/* Details */}
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm text-white/80 truncate">{item.name}</p>
                                    <p className="text-xs text-primary-400 font-medium">
                                        ${item.price?.toFixed(2)}
                                    </p>
                                </div>

                                {/* Remove Button */}
                                <button
                                    onClick={() => removeFromCart(item.product_id)}
                                    className="p-1.5 text-white/30 hover:text-red-400 
                                               opacity-0 group-hover:opacity-100 transition-all"
                                >
                                    <X className="w-4 h-4" />
                                </button>
                            </motion.div>
                        ))
                    ) : (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="py-8 text-center"
                        >
                            <div className="text-4xl mb-2">🛒</div>
                            <p className="text-sm text-white/50">Your bundle is empty</p>
                            <p className="text-xs text-white/30 mt-1">
                                Add products to build your bundle
                            </p>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Budget & Quality Section */}
            {cart.length > 0 && (
                <div className="p-4 border-t border-white/10 space-y-4">
                    {/* Budget Bar */}
                    <BudgetBar used={cartTotal} total={budget} />

                    {/* Quality Score */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 text-amber-400" />
                            <span className="text-sm text-white/60">Quality Score</span>
                        </div>
                        <div className="flex items-center gap-2">
                            <QualityMeter score={qualityScore} />
                            <span className="text-lg font-bold text-white">
                                {qualityScore.toFixed(1)}/10
                            </span>
                        </div>
                    </div>

                    {/* Total */}
                    <div className="flex justify-between items-center pt-2 border-t border-white/10">
                        <span className="text-white/60">Total</span>
                        <span className="text-xl font-bold text-white">
                            ${cartTotal.toFixed(2)}
                        </span>
                    </div>
                </div>
            )}

            {/* Actions */}
            {cart.length > 0 && (
                <div className="p-4 pt-0 space-y-2">
                    {/* Optimize Button */}
                    <motion.button
                        onClick={handleOptimize}
                        disabled={isOptimizing}
                        className="w-full flex items-center justify-center gap-2 py-3 
                                   bg-gradient-to-r from-primary-500 to-primary-600 
                                   text-white font-medium rounded-xl
                                   disabled:opacity-50 shadow-lg shadow-primary-500/25"
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                    >
                        {isOptimizing ? (
                            <>
                                <motion.div
                                    className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 0.6, repeat: Infinity, ease: 'linear' }}
                                />
                                Optimizing...
                            </>
                        ) : (
                            <>
                                <Zap className="w-5 h-5" />
                                Optimize Bundle
                            </>
                        )}
                    </motion.button>

                    {/* Counterfactual Button */}
                    <button
                        onClick={onCounterfactual}
                        className="w-full flex items-center justify-center gap-2 py-2.5
                                   bg-white/5 hover:bg-white/10 text-white/70 hover:text-white
                                   font-medium rounded-xl transition-colors"
                    >
                        <TrendingUp className="w-4 h-4" />
                        What if I had more budget?
                    </button>
                </div>
            )}
        </div>
    )
}

/**
 * Quality score calculation (simplified)
 */
function calculateQualityScore(cart) {
    if (cart.length === 0) return 0

    // Average rating of items
    const avgRating = cart.reduce((sum, item) => sum + (item.rating || 4), 0) / cart.length

    // Bonus for variety (different categories)
    const categories = new Set(cart.map(item => item.category))
    const varietyBonus = Math.min(categories.size * 0.3, 1)

    // Base score
    const baseScore = (avgRating / 5) * 8 + varietyBonus * 2

    return Math.min(10, Math.max(0, baseScore))
}

/**
 * Visual quality meter
 */
function QualityMeter({ score }) {
    const segments = 10
    const filled = Math.round(score)

    const getColor = (index) => {
        if (index >= filled) return 'bg-white/10'
        if (score >= 8) return 'bg-emerald-500'
        if (score >= 6) return 'bg-amber-500'
        return 'bg-orange-500'
    }

    return (
        <div className="flex gap-0.5">
            {Array.from({ length: segments }).map((_, i) => (
                <motion.div
                    key={i}
                    className={`w-1.5 h-4 rounded-sm ${getColor(i)}`}
                    initial={{ scaleY: 0 }}
                    animate={{ scaleY: 1 }}
                    transition={{ delay: i * 0.05 }}
                />
            ))}
        </div>
    )
}
