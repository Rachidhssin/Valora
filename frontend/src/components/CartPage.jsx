import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
    ShoppingBag, X, Sparkles, Star, TrendingUp,
    Trash2, Plus, Eye, CheckCircle2, Package, DollarSign,
    ShoppingCart, Loader2, ArrowLeft, Shield, Truck, AlertCircle,
    CreditCard, Percent, Tag, Gift, Clock, Zap, ChevronRight
} from 'lucide-react'
import OptimizationModal from './OptimizationModal'

/**
 * FULL PAGE CART - Comprehensive Shopping Experience
 * 
 * Layout:
 * - Left Column (40%): Cart items list
 * - Center Column (35%): Optimization results / Suggestions
 * - Right Column (25%): Selected product details + Summary
 */

export default function CartPage({ 
    isOpen, 
    onClose, 
    cart, 
    cartTotal, 
    budget, 
    userId,
    onRemove, 
    onClear, 
    onOptimize, 
    isOptimizing, 
    optimizationResult,
    setOptimizationResult, 
    onAddToCartFromOptimize,
    addToCart
}) {
    const [selectedProduct, setSelectedProduct] = useState(null)
    const [activeSection, setActiveSection] = useState('cart') // 'cart' | 'optimize'
    const [showOptimizationModal, setShowOptimizationModal] = useState(false)
    const [showProductModal, setShowProductModal] = useState(false)
    const [modalProduct, setModalProduct] = useState(null)
    
    const budgetPercent = Math.min((cartTotal / budget) * 100, 100)
    const isOverBudget = cartTotal > budget
    const remainingBudget = budget - cartTotal
    const savings = optimizationResult ? Math.max(0, cartTotal - (optimizationResult.optimized_total || 0)) : 0

    // Handle product click to show modal
    const handleProductClick = (product) => {
        setModalProduct(product)
        setShowProductModal(true)
    }

    // Open modal when optimization completes
    useEffect(() => {
        if (optimizationResult && optimizationResult.optimized_products?.length > 0) {
            setShowOptimizationModal(true)
        }
    }, [optimizationResult])

    // Auto-select first product when cart opens
    useEffect(() => {
        if (isOpen && cart.length > 0 && !selectedProduct) {
            setSelectedProduct(cart[0])
        }
    }, [isOpen, cart])

    // Handle product swaps in optimization
    const handleSwap = (index, newProduct) => {
        setOptimizationResult(prev => {
            const newProducts = [...prev.optimized_products]
            const oldItem = newProducts[index]
            const altWithSlot = { ...newProduct, slot_id: oldItem.slot_id, is_suggestion: oldItem.is_suggestion }
            newProducts[index] = altWithSlot
            
            const newTotal = newProducts.reduce((sum, p) => sum + (p.price || 0), 0)
            
            const slotId = oldItem.slot_id || `suggestion_${index}`
            const currentAlts = prev.alternatives?.[slotId] || []
            const newAlternatives = { ...prev.alternatives }
            newAlternatives[slotId] = [
                oldItem,
                ...currentAlts.filter(a => a.product_id !== newProduct.product_id)
            ].slice(0, 4)
            
            return {
                ...prev,
                optimized_products: newProducts,
                optimized_total: newTotal,
                alternatives: newAlternatives
            }
        })
    }

    const applyOptimizedBundle = () => {
        if (optimizationResult?.optimized_products) {
            onClear()
            optimizationResult.optimized_products.forEach(item => {
                onAddToCartFromOptimize(item)
            })
            setOptimizationResult(null)
            setActiveSection('cart')
        }
    }

    if (!isOpen) return null

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-[#08080c] overflow-hidden"
        >
            {/* Background Effects */}
            <div className="absolute inset-0 pointer-events-none overflow-hidden">
                <div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-violet-600/10 rounded-full blur-[150px]" />
                <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[150px]" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-purple-600/5 rounded-full blur-[200px]" />
            </div>

            {/* Main Content */}
            <div className="relative h-full flex flex-col">
                {/* Header */}
                <CartHeader 
                    onClose={onClose}
                    cart={cart}
                    cartTotal={cartTotal}
                    budget={budget}
                    isOverBudget={isOverBudget}
                    remainingBudget={remainingBudget}
                    optimizationResult={optimizationResult}
                    onOptimize={onOptimize}
                    isOptimizing={isOptimizing}
                />

                {/* Main Grid Layout */}
                <div className="flex-1 overflow-hidden grid grid-cols-12 gap-6 p-6">
                    {/* Left Column - Cart Items */}
                    <div className="col-span-8 flex flex-col overflow-hidden">
                        <CartItemsSection 
                            cart={cart}
                            onRemove={onRemove}
                            onProductClick={handleProductClick}
                            onClear={onClear}
                        />
                    </div>

                    {/* Right Column - Order Summary */}
                    <div className="col-span-4 flex flex-col overflow-hidden">
                        <OrderSummary 
                            cart={cart}
                            cartTotal={cartTotal}
                            budget={budget}
                            isOverBudget={isOverBudget}
                            remainingBudget={remainingBudget}
                            optimizationResult={optimizationResult}
                        />
                    </div>
                </div>
            </div>

            {/* Product Info Modal */}
            <ProductInfoModal 
                isOpen={showProductModal}
                onClose={() => setShowProductModal(false)}
                product={modalProduct}
                onRemove={onRemove}
            />

            {/* Optimization Modal */}
            <OptimizationModal
                isOpen={showOptimizationModal}
                onClose={() => setShowOptimizationModal(false)}
                optimizationResult={optimizationResult}
                cart={cart}
                addToCart={addToCart}
                onSwap={handleSwap}
                onApply={() => {
                    applyOptimizedBundle()
                    setShowOptimizationModal(false)
                }}
                budget={budget}
            />
        </motion.div>
    )
}


// ============================================================================
// HEADER
// ============================================================================
function CartHeader({ onClose, cart, cartTotal, budget, isOverBudget, remainingBudget, optimizationResult, onOptimize, isOptimizing }) {
    const budgetPercent = Math.min((cartTotal / budget) * 100, 100)
    const optimizedPercent = optimizationResult?.optimized_total 
        ? Math.min((optimizationResult.optimized_total / budget) * 100, 100) 
        : 0

    return (
        <div className="relative border-b border-white/[0.06] bg-gradient-to-r from-white/[0.02] to-transparent">
            <div className="px-6 py-4">
                <div className="flex items-center justify-between">
                    {/* Left - Back & Title */}
                    <div className="flex items-center gap-6">
                        <motion.button
                            whileHover={{ scale: 1.05, x: -3 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={onClose}
                            className="flex items-center gap-2 px-4 py-2 bg-white/[0.03] hover:bg-white/[0.06] 
                                     border border-white/[0.08] rounded-xl text-white/60 hover:text-white transition-all"
                        >
                            <ArrowLeft className="w-4 h-4" />
                            <span className="text-sm font-medium">Continue Shopping</span>
                        </motion.button>

                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <div className="p-3 bg-gradient-to-br from-violet-500/20 to-purple-600/10 
                                              rounded-2xl border border-violet-500/20">
                                    <ShoppingCart className="w-7 h-7 text-violet-400" />
                                </div>
                                {cart.length > 0 && (
                                    <motion.div 
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        className="absolute -top-2 -right-2 w-6 h-6 bg-gradient-to-r from-violet-500 to-purple-500 
                                                 rounded-full flex items-center justify-center text-xs font-bold shadow-lg"
                                    >
                                        {cart.length}
                                    </motion.div>
                                )}
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-white">Shopping Cart</h1>
                                <p className="text-sm text-white/40">
                                    {cart.length === 0 ? 'Your cart is empty' : `${cart.length} item${cart.length > 1 ? 's' : ''} in your cart`}
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Right - Budget Progress */}
                    <div className="flex items-center gap-8">
                        {/* Budget Bar */}
                        <div className="w-80">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs text-white/50">Budget Progress</span>
                                <div className="flex items-center gap-2">
                                    <span className={`text-sm font-bold ${isOverBudget ? 'text-red-400' : 'text-white'}`}>
                                        ${cartTotal.toFixed(0)}
                                    </span>
                                    <span className="text-xs text-white/30">/ ${budget}</span>
                                </div>
                            </div>
                            <div className="relative h-2.5 bg-white/[0.05] rounded-full overflow-hidden">
                                {/* Optimized indicator (ghost) */}
                                {optimizationResult && (
                                    <div 
                                        style={{ width: `${budgetPercent}%` }}
                                        className="absolute h-full bg-white/10 rounded-full"
                                    />
                                )}
                                {/* Main progress */}
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${optimizationResult ? optimizedPercent : budgetPercent}%` }}
                                    transition={{ duration: 0.6, ease: 'easeOut' }}
                                    className={`absolute h-full rounded-full ${
                                        optimizationResult 
                                            ? 'bg-gradient-to-r from-emerald-500 via-cyan-500 to-emerald-400'
                                            : isOverBudget 
                                                ? 'bg-gradient-to-r from-red-500 via-orange-500 to-red-400' 
                                                : 'bg-gradient-to-r from-violet-500 via-purple-500 to-violet-400'
                                    }`}
                                >
                                    <div className="absolute inset-0 bg-gradient-to-r from-white/20 to-transparent" />
                                </motion.div>
                            </div>
                            <div className="flex justify-between mt-1">
                                <span className={`text-[10px] ${isOverBudget ? 'text-red-400' : 'text-emerald-400'}`}>
                                    {isOverBudget ? `$${Math.abs(remainingBudget).toFixed(0)} over budget` : `$${remainingBudget.toFixed(0)} remaining`}
                                </span>
                            </div>
                        </div>

                        {/* Optimize Button or Savings Badge */}
                        {optimizationResult ? (
                            <motion.div 
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl"
                            >
                                <TrendingUp className="w-4 h-4 text-emerald-400" />
                                <span className="text-sm font-medium text-emerald-400">
                                    Save ${(cartTotal - optimizationResult.optimized_total).toFixed(0)} with AI Bundle
                                </span>
                            </motion.div>
                        ) : cart.length > 0 && (
                            <motion.button
                                initial={{ opacity: 0, scale: 0.9 }}
                                animate={{ opacity: 1, scale: 1 }}
                                whileHover={{ scale: 1.03 }}
                                whileTap={{ scale: 0.97 }}
                                onClick={onOptimize}
                                disabled={isOptimizing}
                                className="relative px-5 py-2.5 bg-gradient-to-r from-violet-500 via-purple-500 to-violet-600 
                                         hover:from-violet-600 hover:via-purple-600 hover:to-violet-700 rounded-xl text-sm font-semibold 
                                         flex items-center gap-2.5 disabled:opacity-50 shadow-lg shadow-violet-500/30
                                         overflow-hidden group"
                            >
                                {/* Shimmer effect */}
                                <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent 
                                              -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                                {isOptimizing ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin relative" />
                                        <span className="relative">Optimizing...</span>
                                    </>
                                ) : (
                                    <>
                                        <Sparkles className="w-4 h-4 relative" />
                                        <span className="relative">Optimize Bundle</span>
                                    </>
                                )}
                            </motion.button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    )
}


// ============================================================================
// CART ITEMS SECTION
// ============================================================================
function CartItemsSection({ cart, onRemove, onProductClick, onClear }) {
    if (cart.length === 0) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <EmptyCartState />
            </div>
        )
    }

    return (
        <div className="flex flex-col h-full bg-gradient-to-br from-white/[0.02] to-transparent 
                       border border-white/[0.06] rounded-2xl overflow-hidden">
            {/* Section Header */}
            <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-violet-500/10 rounded-xl">
                        <ShoppingBag className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-white">Your Items</h2>
                        <p className="text-xs text-white/40">{cart.length} product{cart.length > 1 ? 's' : ''} selected</p>
                    </div>
                </div>
                <button
                    onClick={onClear}
                    className="px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-red-500/10 
                             rounded-lg transition-all flex items-center gap-1.5"
                >
                    <Trash2 className="w-3.5 h-3.5" />
                    Clear All
                </button>
            </div>

            {/* Items Grid */}
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
                <div className="grid grid-cols-2 gap-4">
                    <AnimatePresence>
                        {cart.map((item, index) => (
                            <CartItemCard
                                key={item.product_id || index}
                                item={item}
                                index={index}
                                onRemove={onRemove}
                                onInfoClick={() => onProductClick(item)}
                            />
                        ))}
                    </AnimatePresence>
                </div>
            </div>
        </div>
    )
}

function CartItemCard({ item, index, onRemove, onInfoClick }) {
    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.8 }}
            transition={{ delay: index * 0.05 }}
            className="relative p-4 rounded-2xl bg-gradient-to-br from-white/[0.03] to-transparent 
                      border border-white/[0.06] hover:border-violet-500/30 transition-all group"
        >
            {/* Number Badge */}
            <div className="absolute -top-2 -left-2 w-7 h-7 bg-gradient-to-br from-violet-500 to-purple-600 
                          rounded-lg flex items-center justify-center text-xs font-bold shadow-lg z-10">
                {index + 1}
            </div>

            {/* Actions */}
            <div className="absolute top-2 right-2 flex gap-1">
                <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={onInfoClick}
                    className="p-1.5 bg-white/[0.05] hover:bg-violet-500/20 text-white/40 hover:text-violet-400 
                             rounded-lg transition-all"
                >
                    <Eye className="w-3.5 h-3.5" />
                </motion.button>
                <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.9 }}
                    onClick={() => onRemove(item.product_id)}
                    className="p-1.5 bg-white/[0.05] hover:bg-red-500/20 text-white/40 hover:text-red-400 
                             rounded-lg transition-all"
                >
                    <X className="w-3.5 h-3.5" />
                </motion.button>
            </div>

            {/* Image */}
            <div className="relative w-full aspect-square bg-gradient-to-br from-white/[0.04] to-transparent 
                          rounded-xl overflow-hidden mb-3">
                {item.image_url ? (
                    <img
                        src={item.image_url}
                        alt={item.name}
                        className="w-full h-full object-contain p-3 group-hover:scale-105 transition-transform"
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-3xl">📦</div>
                )}
            </div>

            {/* Info */}
            <div className="space-y-2">
                {item.brand && item.brand !== 'Unknown' && (
                    <p className="text-[10px] text-violet-400 font-semibold uppercase tracking-wider">
                        {item.brand}
                    </p>
                )}
                <h4 className="text-sm text-white/90 font-medium leading-snug line-clamp-2">
                    {item.name}
                </h4>
                
                <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-2">
                        {item.rating > 0 && (
                            <span className="flex items-center gap-1 text-[10px] text-amber-400">
                                <Star className="w-3 h-3 fill-amber-400" />
                                {item.rating?.toFixed(1)}
                            </span>
                        )}
                    </div>
                    <p className="text-lg font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                        ${item.price?.toFixed(0)}
                    </p>
                </div>
            </div>
        </motion.div>
    )
}

function EmptyCartState() {
    return (
        <div className="text-center p-8">
            <motion.div 
                animate={{ y: [0, -10, 0] }}
                transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                className="relative w-32 h-32 mx-auto mb-6"
            >
                <div className="absolute inset-0 bg-gradient-to-br from-violet-500/20 to-cyan-500/20 rounded-full blur-2xl" />
                <div className="absolute inset-4 bg-gradient-to-br from-white/[0.03] to-transparent 
                              rounded-full flex items-center justify-center border border-white/[0.08]">
                    <ShoppingBag className="w-12 h-12 text-white/20" />
                </div>
            </motion.div>
            <h3 className="text-xl font-bold text-white/70 mb-2">Your cart is empty</h3>
            <p className="text-sm text-white/40 max-w-xs mx-auto">
                Start exploring our collection and add products to build your perfect bundle
            </p>
        </div>
    )
}


// ============================================================================
// PRODUCT INFO MODAL
// ============================================================================
function ProductInfoModal({ isOpen, onClose, product, onRemove }) {
    if (!isOpen || !product) return null

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[60] flex items-center justify-center p-6"
            >
                {/* Backdrop */}
                <motion.div 
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    onClick={onClose}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                />

                {/* Modal */}
                <motion.div
                    initial={{ opacity: 0, scale: 0.9, y: 20 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.9, y: 20 }}
                    transition={{ type: 'spring', damping: 25 }}
                    className="relative w-full max-w-lg bg-[#0c0c10] border border-white/[0.08] rounded-3xl 
                              overflow-hidden shadow-2xl shadow-black/50"
                >
                    {/* Close Button */}
                    <motion.button
                        whileHover={{ scale: 1.1, rotate: 90 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={onClose}
                        className="absolute top-4 right-4 z-10 p-2 bg-white/[0.05] hover:bg-white/[0.1] 
                                 rounded-xl transition-colors"
                    >
                        <X className="w-5 h-5 text-white/60" />
                    </motion.button>

                    {/* Image Section */}
                    <div className="relative aspect-square bg-gradient-to-br from-white/[0.03] to-transparent">
                        {product.image_url ? (
                            <img 
                                src={product.image_url} 
                                alt={product.name}
                                className="w-full h-full object-contain p-8"
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center text-6xl">📦</div>
                        )}
                        
                        {/* Gradient Overlay */}
                        <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0c0c10] to-transparent" />
                    </div>

                    {/* Content */}
                    <div className="p-6 -mt-16 relative">
                        {/* Brand Badge */}
                        {product.brand && product.brand !== 'Unknown' && (
                            <span className="inline-block px-3 py-1 bg-violet-500/20 border border-violet-500/30 
                                           rounded-full text-xs text-violet-400 font-semibold mb-3">
                                {product.brand}
                            </span>
                        )}

                        {/* Name */}
                        <h2 className="text-xl font-bold text-white leading-snug mb-3">
                            {product.name}
                        </h2>

                        {/* Price & Rating Row */}
                        <div className="flex items-center justify-between mb-4">
                            <p className="text-3xl font-bold bg-gradient-to-r from-violet-400 via-purple-400 to-cyan-400 
                                        bg-clip-text text-transparent">
                                ${product.price?.toFixed(2)}
                            </p>
                            {product.rating > 0 && (
                                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                                    <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                                    <span className="text-sm text-amber-400 font-semibold">{product.rating?.toFixed(1)}</span>
                                    {product.review_count > 0 && (
                                        <span className="text-xs text-amber-400/60">({product.review_count})</span>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Category */}
                        {product.category && (
                            <div className="flex items-center gap-2 mb-4">
                                <Tag className="w-4 h-4 text-white/30" />
                                <span className="text-sm text-white/50">{product.category.split(',')[0]}</span>
                            </div>
                        )}

                        {/* Description */}
                        {product.description && (
                            <p className="text-sm text-white/50 leading-relaxed mb-6 line-clamp-4">
                                {product.description}
                            </p>
                        )}

                        {/* Action Buttons */}
                        <div className="flex gap-3">
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={() => {
                                    onRemove(product.product_id)
                                    onClose()
                                }}
                                className="flex-1 py-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 
                                         rounded-xl text-sm font-medium text-red-400 flex items-center justify-center gap-2"
                            >
                                <Trash2 className="w-4 h-4" />
                                Remove from Cart
                            </motion.button>
                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                onClick={onClose}
                                className="flex-1 py-3 bg-gradient-to-r from-violet-500 to-purple-500 
                                         rounded-xl text-sm font-semibold flex items-center justify-center gap-2"
                            >
                                <CheckCircle2 className="w-4 h-4" />
                                Keep in Cart
                            </motion.button>
                        </div>
                    </div>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    )
}


// ============================================================================
// ORDER SUMMARY (Enhanced)
// ============================================================================
function OrderSummary({ cart, cartTotal, budget, isOverBudget, remainingBudget, optimizationResult }) {
    const itemCount = cart.length
    const optimizedTotal = optimizationResult?.optimized_total
    const avgPrice = itemCount > 0 ? cartTotal / itemCount : 0
    const budgetUsagePercent = Math.min((cartTotal / budget) * 100, 100)

    // Calculate category breakdown
    const categoryBreakdown = cart.reduce((acc, item) => {
        const category = item.category?.split(',')[0] || 'Other'
        acc[category] = (acc[category] || 0) + item.price
        return acc
    }, {})

    return (
        <div className="flex-1 flex flex-col bg-gradient-to-br from-white/[0.02] to-transparent border border-white/[0.06] rounded-2xl overflow-hidden">
            {/* Header */}
            <div className="px-5 py-4 border-b border-white/[0.06] bg-gradient-to-r from-violet-500/5 to-transparent">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-violet-500/20 to-purple-500/10 rounded-xl">
                        <CreditCard className="w-5 h-5 text-violet-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-white">Order Summary</h3>
                        <p className="text-xs text-white/40">{itemCount} item{itemCount !== 1 ? 's' : ''} in cart</p>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-5 custom-scrollbar">
                {/* Budget Usage Visual */}
                <div className="p-4 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                    <div className="flex items-center justify-between mb-3">
                        <span className="text-xs text-white/50 flex items-center gap-2">
                            <DollarSign className="w-3.5 h-3.5" />
                            Budget Usage
                        </span>
                        <span className={`text-sm font-bold ${isOverBudget ? 'text-red-400' : 'text-emerald-400'}`}>
                            {budgetUsagePercent.toFixed(0)}%
                        </span>
                    </div>
                    <div className="relative h-3 bg-white/[0.05] rounded-full overflow-hidden">
                        <motion.div
                            initial={{ width: 0 }}
                            animate={{ width: `${Math.min(budgetUsagePercent, 100)}%` }}
                            transition={{ duration: 0.5 }}
                            className={`h-full rounded-full ${
                                isOverBudget 
                                    ? 'bg-gradient-to-r from-red-500 to-orange-500' 
                                    : budgetUsagePercent > 80 
                                        ? 'bg-gradient-to-r from-amber-500 to-yellow-500'
                                        : 'bg-gradient-to-r from-emerald-500 to-cyan-500'
                            }`}
                        />
                    </div>
                    <div className="flex justify-between mt-2 text-[10px] text-white/40">
                        <span>$0</span>
                        <span>${budget}</span>
                    </div>
                </div>

                {/* Price Breakdown */}
                <div className="space-y-3">
                    <p className="text-xs text-white/40 uppercase tracking-wider flex items-center gap-2">
                        <Package className="w-3.5 h-3.5" />
                        Price Breakdown
                    </p>
                    
                    <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                            <span className="text-white/60">Subtotal ({itemCount} items)</span>
                            <span className="text-white font-medium">${cartTotal.toFixed(2)}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-white/60">Avg. per item</span>
                            <span className="text-white/80">${avgPrice.toFixed(2)}</span>
                        </div>
                        {cartTotal >= 50 && (
                            <div className="flex justify-between text-sm">
                                <span className="text-emerald-400/80 flex items-center gap-1">
                                    <Truck className="w-3.5 h-3.5" />
                                    Free Shipping
                                </span>
                                <span className="text-emerald-400 line-through">$9.99</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Category Breakdown */}
                {Object.keys(categoryBreakdown).length > 0 && (
                    <div className="space-y-3">
                        <p className="text-xs text-white/40 uppercase tracking-wider flex items-center gap-2">
                            <Tag className="w-3.5 h-3.5" />
                            By Category
                        </p>
                        <div className="space-y-2">
                            {Object.entries(categoryBreakdown).slice(0, 4).map(([category, amount]) => (
                                <div key={category} className="flex items-center justify-between">
                                    <span className="text-xs text-white/50 truncate max-w-[120px]">{category}</span>
                                    <div className="flex items-center gap-2">
                                        <div className="w-16 h-1.5 bg-white/[0.05] rounded-full overflow-hidden">
                                            <div 
                                                className="h-full bg-gradient-to-r from-violet-500 to-purple-500 rounded-full"
                                                style={{ width: `${(amount / cartTotal) * 100}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-white/70 w-12 text-right">${amount.toFixed(0)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* AI Savings */}
                {optimizedTotal && optimizedTotal < cartTotal && (
                    <motion.div 
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="p-4 bg-gradient-to-r from-emerald-500/10 to-cyan-500/10 border border-emerald-500/20 rounded-xl"
                    >
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-1.5 bg-emerald-500/20 rounded-lg">
                                <Sparkles className="w-4 h-4 text-emerald-400" />
                            </div>
                            <span className="text-sm font-semibold text-emerald-400">AI Optimization Available</span>
                        </div>
                        <div className="flex items-center justify-between">
                            <span className="text-xs text-emerald-400/70">Potential savings</span>
                            <span className="text-lg font-bold text-emerald-400">-${(cartTotal - optimizedTotal).toFixed(2)}</span>
                        </div>
                    </motion.div>
                )}

                {/* Features */}
                <div className="grid grid-cols-2 gap-2">
                    <div className="flex items-center gap-2 p-2.5 bg-white/[0.02] border border-white/[0.04] rounded-lg">
                        <Shield className="w-4 h-4 text-violet-400/60" />
                        <span className="text-[10px] text-white/40">Secure Payment</span>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 bg-white/[0.02] border border-white/[0.04] rounded-lg">
                        <Clock className="w-4 h-4 text-cyan-400/60" />
                        <span className="text-[10px] text-white/40">Fast Delivery</span>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 bg-white/[0.02] border border-white/[0.04] rounded-lg">
                        <Gift className="w-4 h-4 text-purple-400/60" />
                        <span className="text-[10px] text-white/40">Gift Wrapping</span>
                    </div>
                    <div className="flex items-center gap-2 p-2.5 bg-white/[0.02] border border-white/[0.04] rounded-lg">
                        <Zap className="w-4 h-4 text-amber-400/60" />
                        <span className="text-[10px] text-white/40">Express Option</span>
                    </div>
                </div>
            </div>

            {/* Footer - Total & Status */}
            <div className="p-5 border-t border-white/[0.06] bg-gradient-to-r from-white/[0.02] to-transparent">
                {/* Total */}
                <div className="flex items-center justify-between mb-4">
                    <span className="text-white/70">Total</span>
                    <div className="text-right">
                        <p className={`text-2xl font-bold ${isOverBudget ? 'text-red-400' : 'text-white'}`}>
                            ${(optimizedTotal || cartTotal).toFixed(2)}
                        </p>
                        {optimizedTotal && optimizedTotal < cartTotal && (
                            <p className="text-xs text-white/40 line-through">${cartTotal.toFixed(2)}</p>
                        )}
                    </div>
                </div>

                {/* Budget Status */}
                <div className={`flex items-center justify-between px-4 py-3 rounded-xl ${
                    isOverBudget 
                        ? 'bg-red-500/10 border border-red-500/20' 
                        : 'bg-emerald-500/10 border border-emerald-500/20'
                }`}>
                    <div className="flex items-center gap-2">
                        {isOverBudget ? (
                            <AlertCircle className="w-5 h-5 text-red-400" />
                        ) : (
                            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        )}
                        <span className={`text-sm font-medium ${isOverBudget ? 'text-red-400' : 'text-emerald-400'}`}>
                            {isOverBudget ? 'Over Budget' : 'Within Budget'}
                        </span>
                    </div>
                    <span className={`text-sm font-bold ${isOverBudget ? 'text-red-400' : 'text-emerald-400'}`}>
                        {isOverBudget ? '+' : '-'}${Math.abs(remainingBudget).toFixed(0)}
                    </span>
                </div>

                {/* Checkout Button */}
                <motion.button
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    className="w-full mt-4 py-4 bg-gradient-to-r from-violet-500 via-purple-500 to-violet-600 
                             rounded-xl text-sm font-bold flex items-center justify-center gap-2 
                             shadow-lg shadow-violet-500/20 group"
                >
                    <span>Proceed to Checkout</span>
                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                </motion.button>
            </div>
        </div>
    )
}
