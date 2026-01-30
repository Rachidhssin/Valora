import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
    Sparkles, X, Check, Star, TrendingUp, ArrowLeftRight,
    ChevronRight, Package, DollarSign, Percent, RefreshCw,
    Plus, CheckCircle2, Zap, ArrowRight, Target, Award,
    ShoppingBag, Eye, ArrowDown, Layers, Replace, Crown,
    ThumbsUp, Flame, Gift, BadgeCheck
} from 'lucide-react'

/**
 * OPTIMIZATION MODAL - Full Screen Bundle Optimization Experience
 * 
 * Features:
 * - Dramatic entrance animation
 * - Split view: Optimized products (left) + Selected product details (right)
 * - Beautiful alternative product cards with comparison
 * - One-click swap functionality
 * - Visual savings indicators
 */

export default function OptimizationModal({
    isOpen,
    onClose,
    optimizationResult,
    cart,
    addToCart,
    onSwap,
    onApply,
    budget
}) {
    const [selectedProduct, setSelectedProduct] = useState(null)
    const [selectedIndex, setSelectedIndex] = useState(null)
    const [viewingAlternatives, setViewingAlternatives] = useState(false)

    // Auto-select first product
    useEffect(() => {
        if (isOpen && optimizationResult?.optimized_products?.length > 0) {
            setSelectedProduct(optimizationResult.optimized_products[0])
            setSelectedIndex(0)
        }
    }, [isOpen, optimizationResult])

    if (!isOpen || !optimizationResult) return null

    const { optimized_products, optimized_total, alternatives } = optimizationResult
    const originalTotal = cart.reduce((sum, p) => sum + (p.price || 0), 0)
    const savings = Math.max(0, originalTotal - optimized_total)
    const savingsPercent = originalTotal > 0 ? ((savings / originalTotal) * 100).toFixed(0) : 0

    const handleSelectProduct = (product, index) => {
        setSelectedProduct(product)
        setSelectedIndex(index)
        setViewingAlternatives(false)
    }

    const handleViewAlternatives = () => {
        setViewingAlternatives(true)
    }

    const handleSwapProduct = (altProduct) => {
        onSwap(selectedIndex, altProduct)
        setSelectedProduct(altProduct)
        setViewingAlternatives(false)
    }

    const currentAlternatives = selectedProduct 
        ? alternatives?.[selectedProduct.slot_id || `suggestion_${selectedIndex}`] || []
        : []

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 z-[100] overflow-hidden"
            >
                {/* Animated Background */}
                <div className="absolute inset-0 bg-[#06060a]">
                    {/* Gradient Orbs */}
                    <motion.div
                        animate={{ 
                            x: [0, 100, 0],
                            y: [0, -50, 0],
                            scale: [1, 1.2, 1]
                        }}
                        transition={{ duration: 20, repeat: Infinity, ease: 'easeInOut' }}
                        className="absolute -top-40 -left-40 w-[700px] h-[700px] bg-gradient-to-br from-emerald-600/20 via-cyan-600/10 to-transparent rounded-full blur-[150px]"
                    />
                    <motion.div
                        animate={{ 
                            x: [0, -80, 0],
                            y: [0, 60, 0],
                            scale: [1, 1.1, 1]
                        }}
                        transition={{ duration: 15, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
                        className="absolute -bottom-40 -right-40 w-[600px] h-[600px] bg-gradient-to-tl from-violet-600/20 via-purple-600/10 to-transparent rounded-full blur-[150px]"
                    />
                    <motion.div
                        animate={{ 
                            scale: [1, 1.3, 1],
                            opacity: [0.5, 0.8, 0.5]
                        }}
                        transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
                        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-gradient-to-br from-cyan-500/10 to-emerald-500/5 rounded-full blur-[100px]"
                    />
                    
                    {/* Grid Pattern */}
                    <div className="absolute inset-0 opacity-[0.02]" 
                         style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, white 1px, transparent 0)', backgroundSize: '40px 40px' }} 
                    />
                </div>

                {/* Content */}
                <div className="relative h-full flex flex-col">
                    {/* Header */}
                    <ModalHeader 
                        onClose={onClose}
                        optimized_total={optimized_total}
                        savings={savings}
                        savingsPercent={savingsPercent}
                        productCount={optimized_products?.length || 0}
                        budget={budget}
                    />

                    {/* Main Content Grid */}
                    <div className="flex-1 overflow-hidden grid grid-cols-12 gap-6 p-6">
                        {/* Left - Product List */}
                        <div className="col-span-5 flex flex-col overflow-hidden">
                            <ProductListSection 
                                products={optimized_products}
                                selectedProduct={selectedProduct}
                                selectedIndex={selectedIndex}
                                onSelectProduct={handleSelectProduct}
                                cart={cart}
                                alternatives={alternatives}
                            />
                        </div>

                        {/* Right - Product Detail / Alternatives */}
                        <div className="col-span-7 flex flex-col overflow-hidden">
                            <AnimatePresence mode="wait">
                                {viewingAlternatives ? (
                                    <AlternativesSection 
                                        key="alternatives"
                                        currentProduct={selectedProduct}
                                        alternatives={currentAlternatives}
                                        onSwap={handleSwapProduct}
                                        onBack={() => setViewingAlternatives(false)}
                                        cart={cart}
                                    />
                                ) : (
                                    <ProductDetailSection 
                                        key="details"
                                        product={selectedProduct}
                                        index={selectedIndex}
                                        alternativesCount={currentAlternatives.length}
                                        onViewAlternatives={handleViewAlternatives}
                                        cart={cart}
                                        addToCart={addToCart}
                                    />
                                )}
                            </AnimatePresence>
                        </div>
                    </div>

                    {/* Footer */}
                    <ModalFooter 
                        onClose={onClose}
                        onApply={onApply}
                        optimized_total={optimized_total}
                        savings={savings}
                    />
                </div>
            </motion.div>
        </AnimatePresence>
    )
}


// ============================================================================
// MODAL HEADER
// ============================================================================
function ModalHeader({ onClose, optimized_total, savings, savingsPercent, productCount, budget }) {
    return (
        <motion.div 
            initial={{ y: -50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.1 }}
            className="relative border-b border-white/[0.06] bg-gradient-to-r from-emerald-500/5 via-transparent to-violet-500/5"
        >
            <div className="px-8 py-5">
                <div className="flex items-center justify-between">
                    {/* Left - Title */}
                    <div className="flex items-center gap-5">
                        <motion.div 
                            initial={{ scale: 0, rotate: -180 }}
                            animate={{ scale: 1, rotate: 0 }}
                            transition={{ type: 'spring', damping: 12, delay: 0.2 }}
                            className="relative"
                        >
                            <div className="p-4 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-2xl shadow-2xl shadow-emerald-500/30">
                                <Sparkles className="w-8 h-8 text-white" />
                            </div>
                            <motion.div
                                animate={{ scale: [1, 1.5, 1], opacity: [0.5, 0, 0.5] }}
                                transition={{ duration: 2, repeat: Infinity }}
                                className="absolute inset-0 bg-emerald-400/30 rounded-2xl"
                            />
                        </motion.div>
                        
                        <div>
                            <motion.h1 
                                initial={{ x: -20, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: 0.3 }}
                                className="text-3xl font-bold bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 bg-clip-text text-transparent"
                            >
                                Your Optimized Bundle
                            </motion.h1>
                            <motion.p 
                                initial={{ x: -20, opacity: 0 }}
                                animate={{ x: 0, opacity: 1 }}
                                transition={{ delay: 0.4 }}
                                className="text-sm text-white/50 mt-1"
                            >
                                AI-curated selection maximized for your ${budget} budget
                            </motion.p>
                        </div>
                    </div>

                    {/* Center - Stats */}
                    <motion.div 
                        initial={{ y: -20, opacity: 0 }}
                        animate={{ y: 0, opacity: 1 }}
                        transition={{ delay: 0.4 }}
                        className="flex items-center gap-4"
                    >
                        <StatPill 
                            icon={<Package className="w-4 h-4" />}
                            value={productCount}
                            label="Products"
                            color="violet"
                        />
                        <StatPill 
                            icon={<DollarSign className="w-4 h-4" />}
                            value={`$${optimized_total?.toFixed(0)}`}
                            label="Total"
                            color="cyan"
                        />
                        <StatPill 
                            icon={<TrendingUp className="w-4 h-4" />}
                            value={`$${savings.toFixed(0)}`}
                            label="Saved"
                            color="emerald"
                            highlight
                        />
                    </motion.div>

                    {/* Right - Close */}
                    <motion.button
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ delay: 0.3 }}
                        whileHover={{ scale: 1.1, rotate: 90 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={onClose}
                        className="p-3 bg-white/[0.03] hover:bg-white/[0.08] border border-white/[0.06] 
                                 rounded-xl transition-colors"
                    >
                        <X className="w-5 h-5 text-white/50" />
                    </motion.button>
                </div>
            </div>
        </motion.div>
    )
}

function StatPill({ icon, value, label, color, highlight }) {
    const colors = {
        violet: 'from-violet-500/20 to-violet-500/5 border-violet-500/30 text-violet-400',
        cyan: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/30 text-cyan-400',
        emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30 text-emerald-400'
    }

    return (
        <div className={`relative flex items-center gap-3 px-4 py-2.5 bg-gradient-to-r ${colors[color]} border rounded-xl`}>
            {highlight && (
                <motion.div
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute inset-0 bg-emerald-500/10 rounded-xl"
                />
            )}
            <div className="relative">
                {icon}
            </div>
            <div className="relative">
                <p className="text-lg font-bold">{value}</p>
                <p className="text-[10px] opacity-60 -mt-0.5">{label}</p>
            </div>
        </div>
    )
}


// ============================================================================
// PRODUCT LIST SECTION
// ============================================================================
function ProductListSection({ products, selectedProduct, selectedIndex, onSelectProduct, cart, alternatives }) {
    return (
        <motion.div 
            initial={{ x: -50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex flex-col h-full bg-gradient-to-br from-white/[0.03] to-transparent 
                      border border-white/[0.06] rounded-3xl overflow-hidden"
        >
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/[0.06] bg-gradient-to-r from-white/[0.02] to-transparent">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-gradient-to-br from-emerald-500/20 to-cyan-500/10 rounded-xl">
                        <Layers className="w-5 h-5 text-emerald-400" />
                    </div>
                    <div>
                        <h2 className="text-lg font-semibold text-white">Bundle Products</h2>
                        <p className="text-xs text-white/40">Click to view details • Swap for alternatives</p>
                    </div>
                </div>
            </div>

            {/* Product List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                {products?.map((product, index) => {
                    const isFromCart = !product.is_suggestion
                    const isSelected = selectedIndex === index
                    const altCount = alternatives?.[product.slot_id || `suggestion_${index}`]?.length || 0
                    const isInCart = cart.some(c => c.product_id === product.product_id)

                    return (
                        <motion.div
                            key={product.product_id || index}
                            initial={{ x: -30, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            transition={{ delay: 0.3 + index * 0.08 }}
                            onClick={() => onSelectProduct(product, index)}
                            className={`relative p-4 rounded-2xl cursor-pointer transition-all duration-300 group
                                      ${isSelected 
                                          ? 'bg-gradient-to-r from-emerald-500/15 via-cyan-500/10 to-violet-500/15 border-2 border-emerald-500/40 shadow-xl shadow-emerald-500/10' 
                                          : 'bg-white/[0.02] border border-white/[0.06] hover:border-emerald-500/30 hover:bg-white/[0.04]'
                                      }`}
                        >
                            <div className="flex gap-4">
                                {/* Number Badge */}
                                <div className={`absolute -top-2 -left-2 w-8 h-8 rounded-xl flex items-center justify-center 
                                               text-sm font-bold shadow-lg z-10
                                               ${isSelected 
                                                   ? 'bg-gradient-to-br from-emerald-500 to-cyan-500' 
                                                   : 'bg-gradient-to-br from-violet-500 to-purple-600'
                                               }`}>
                                    {index + 1}
                                </div>

                                {/* Image */}
                                <div className="relative w-20 h-20 bg-gradient-to-br from-white/[0.06] to-transparent 
                                              rounded-xl overflow-hidden flex-shrink-0">
                                    {product.image_url ? (
                                        <img
                                            src={product.image_url}
                                            alt={product.name}
                                            className="w-full h-full object-contain p-2 group-hover:scale-110 transition-transform"
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-2xl">📦</div>
                                    )}
                                </div>

                                {/* Info */}
                                <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        {isFromCart && (
                                            <span className="px-2 py-0.5 bg-emerald-500/20 border border-emerald-500/30 
                                                           rounded-full text-[9px] text-emerald-400 font-medium flex items-center gap-1">
                                                <ShoppingBag className="w-2.5 h-2.5" />
                                                From Cart
                                            </span>
                                        )}
                                        {product.is_suggestion && (
                                            <span className="px-2 py-0.5 bg-cyan-500/20 border border-cyan-500/30 
                                                           rounded-full text-[9px] text-cyan-400 font-medium flex items-center gap-1">
                                                <Sparkles className="w-2.5 h-2.5" />
                                                AI Pick
                                            </span>
                                        )}
                                        {altCount > 0 && (
                                            <span className="px-2 py-0.5 bg-violet-500/20 border border-violet-500/30 
                                                           rounded-full text-[9px] text-violet-400 font-medium flex items-center gap-1">
                                                <ArrowLeftRight className="w-2.5 h-2.5" />
                                                {altCount} Alternatives
                                            </span>
                                        )}
                                    </div>

                                    {product.brand && product.brand !== 'Unknown' && (
                                        <p className="text-[10px] text-violet-400 font-semibold uppercase tracking-wider mb-0.5">
                                            {product.brand}
                                        </p>
                                    )}

                                    <h4 className="text-sm text-white/90 font-medium leading-snug line-clamp-2">
                                        {product.name}
                                    </h4>
                                </div>

                                {/* Price */}
                                <div className="text-right flex flex-col justify-between">
                                    <p className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-400 bg-clip-text text-transparent">
                                        ${product.price?.toFixed(0)}
                                    </p>
                                    {product.rating > 0 && (
                                        <div className="flex items-center gap-1 justify-end">
                                            <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                                            <span className="text-xs text-amber-400">{product.rating?.toFixed(1)}</span>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Selection Arrow */}
                            {isSelected && (
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="absolute right-4 top-1/2 -translate-y-1/2"
                                >
                                    <ChevronRight className="w-5 h-5 text-emerald-400" />
                                </motion.div>
                            )}
                        </motion.div>
                    )
                })}
            </div>
        </motion.div>
    )
}


// ============================================================================
// PRODUCT DETAIL SECTION
// ============================================================================
function ProductDetailSection({ product, index, alternativesCount, onViewAlternatives, cart, addToCart }) {
    if (!product) {
        return (
            <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                    <Eye className="w-12 h-12 text-white/10 mx-auto mb-4" />
                    <p className="text-white/40">Select a product to view details</p>
                </div>
            </div>
        )
    }

    const isInCart = cart.some(c => c.product_id === product.product_id)
    const isFromCart = !product.is_suggestion

    const handleAddToCart = () => {
        window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
            detail: {
                x: window.innerWidth / 2,
                y: window.innerHeight / 2,
                productImage: product.image_url,
                productName: product.name,
                productPrice: product.price
            }
        }))
        addToCart(product)
    }

    return (
        <motion.div
            initial={{ x: 50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 50, opacity: 0 }}
            transition={{ delay: 0.2 }}
            className="flex-1 flex flex-col h-full bg-gradient-to-br from-white/[0.03] to-transparent 
                      border border-white/[0.06] rounded-3xl overflow-hidden"
        >
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/[0.06] bg-gradient-to-r from-white/[0.02] to-transparent">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gradient-to-br from-violet-500/20 to-purple-500/10 rounded-xl">
                            <Eye className="w-5 h-5 text-violet-400" />
                        </div>
                        <div>
                            <h2 className="text-lg font-semibold text-white">Product Details</h2>
                            <p className="text-xs text-white/40">Item #{index + 1} in your optimized bundle</p>
                        </div>
                    </div>

                    {/* View Alternatives Button */}
                    {alternativesCount > 0 && (
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={onViewAlternatives}
                            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-cyan-500/20 to-violet-500/20 
                                     border border-cyan-500/30 hover:border-cyan-500/50 rounded-xl text-sm font-medium 
                                     text-cyan-400 transition-all"
                        >
                            <ArrowLeftRight className="w-4 h-4" />
                            View {alternativesCount} Alternatives
                            <ChevronRight className="w-4 h-4" />
                        </motion.button>
                    )}
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                <div className="grid grid-cols-2 gap-6 h-full">
                    {/* Left - Image */}
                    <div className="flex flex-col">
                        <div className="relative aspect-square bg-gradient-to-br from-white/[0.04] to-transparent 
                                      rounded-2xl overflow-hidden border border-white/[0.06]">
                            {product.image_url ? (
                                <img 
                                    src={product.image_url} 
                                    alt={product.name}
                                    className="w-full h-full object-contain p-6"
                                />
                            ) : (
                                <div className="w-full h-full flex items-center justify-center text-6xl">📦</div>
                            )}

                            {/* Badges */}
                            <div className="absolute top-4 left-4 flex flex-col gap-2">
                                {isFromCart && (
                                    <span className="px-3 py-1.5 bg-emerald-500/90 rounded-lg text-xs font-semibold 
                                                   text-white shadow-lg flex items-center gap-1.5">
                                        <ShoppingBag className="w-3.5 h-3.5" />
                                        From Your Cart
                                    </span>
                                )}
                                {product.is_suggestion && (
                                    <span className="px-3 py-1.5 bg-gradient-to-r from-cyan-500 to-violet-500 rounded-lg 
                                                   text-xs font-semibold text-white shadow-lg flex items-center gap-1.5">
                                        <Crown className="w-3.5 h-3.5" />
                                        AI Recommended
                                    </span>
                                )}
                            </div>

                            {/* Number */}
                            <div className="absolute bottom-4 right-4 w-12 h-12 bg-gradient-to-br from-violet-500 to-purple-600 
                                          rounded-xl flex items-center justify-center text-xl font-bold shadow-lg">
                                {index + 1}
                            </div>
                        </div>

                        {/* Quick Stats */}
                        <div className="grid grid-cols-3 gap-3 mt-4">
                            {product.rating > 0 && (
                                <div className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl text-center">
                                    <div className="flex items-center justify-center gap-1 text-amber-400 mb-1">
                                        <Star className="w-4 h-4 fill-amber-400" />
                                        <span className="font-bold">{product.rating?.toFixed(1)}</span>
                                    </div>
                                    <p className="text-[10px] text-white/40">Rating</p>
                                </div>
                            )}
                            {product.review_count > 0 && (
                                <div className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl text-center">
                                    <p className="font-bold text-white/80">{product.review_count}</p>
                                    <p className="text-[10px] text-white/40">Reviews</p>
                                </div>
                            )}
                            <div className="p-3 bg-white/[0.02] border border-white/[0.06] rounded-xl text-center">
                                <div className="flex items-center justify-center gap-1 text-emerald-400 mb-1">
                                    <BadgeCheck className="w-4 h-4" />
                                </div>
                                <p className="text-[10px] text-white/40">Verified</p>
                            </div>
                        </div>
                    </div>

                    {/* Right - Info */}
                    <div className="flex flex-col">
                        {/* Brand */}
                        {product.brand && product.brand !== 'Unknown' && (
                            <p className="text-xs text-violet-400 font-semibold uppercase tracking-wider mb-2">
                                {product.brand}
                            </p>
                        )}

                        {/* Name */}
                        <h3 className="text-2xl font-bold text-white leading-snug mb-4">
                            {product.name}
                        </h3>

                        {/* Category */}
                        {product.category && (
                            <div className="flex items-center gap-2 mb-4">
                                <span className="px-3 py-1 bg-white/[0.05] border border-white/[0.08] 
                                               rounded-lg text-xs text-white/50">
                                    {product.category.split(',')[0]}
                                </span>
                            </div>
                        )}

                        {/* Price */}
                        <div className="mb-6">
                            <p className="text-4xl font-bold bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 
                                        bg-clip-text text-transparent">
                                ${product.price?.toFixed(2)}
                            </p>
                            <p className="text-xs text-white/40 mt-1">Optimized price within your budget</p>
                        </div>

                        {/* Description */}
                        {product.description && (
                            <div className="flex-1 mb-6">
                                <p className="text-sm text-white/50 leading-relaxed line-clamp-5">
                                    {product.description}
                                </p>
                            </div>
                        )}

                        {/* Features */}
                        <div className="space-y-2 mb-6">
                            <div className="flex items-center gap-3 text-sm text-white/60">
                                <div className="p-1.5 bg-emerald-500/10 rounded-lg">
                                    <Check className="w-3.5 h-3.5 text-emerald-400" />
                                </div>
                                <span>Best value in category</span>
                            </div>
                            <div className="flex items-center gap-3 text-sm text-white/60">
                                <div className="p-1.5 bg-cyan-500/10 rounded-lg">
                                    <Check className="w-3.5 h-3.5 text-cyan-400" />
                                </div>
                                <span>Fits within your budget</span>
                            </div>
                            <div className="flex items-center gap-3 text-sm text-white/60">
                                <div className="p-1.5 bg-violet-500/10 rounded-lg">
                                    <Check className="w-3.5 h-3.5 text-violet-400" />
                                </div>
                                <span>Complements other bundle items</span>
                            </div>
                        </div>

                        {/* Action */}
                        <div className="mt-auto">
                            {isInCart ? (
                                <div className="flex items-center justify-center gap-2 py-3 bg-emerald-500/10 
                                              border border-emerald-500/20 rounded-xl">
                                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                                    <span className="text-sm text-emerald-400 font-medium">Already in your cart</span>
                                </div>
                            ) : product.is_suggestion ? (
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={handleAddToCart}
                                    className="w-full py-3 bg-gradient-to-r from-violet-500 to-purple-500 
                                             hover:from-violet-600 hover:to-purple-600 rounded-xl text-sm font-semibold 
                                             flex items-center justify-center gap-2 shadow-lg shadow-violet-500/20"
                                >
                                    <Plus className="w-4 h-4" />
                                    Add to Cart Now
                                </motion.button>
                            ) : (
                                <div className="flex items-center justify-center gap-2 py-3 bg-white/[0.03] 
                                              border border-white/[0.08] rounded-xl">
                                    <ShoppingBag className="w-5 h-5 text-white/40" />
                                    <span className="text-sm text-white/40">This item is from your cart</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}


// ============================================================================
// ALTERNATIVES SECTION
// ============================================================================
function AlternativesSection({ currentProduct, alternatives, onSwap, onBack, cart }) {
    const [hoveredAlt, setHoveredAlt] = useState(null)

    return (
        <motion.div
            initial={{ x: 50, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -50, opacity: 0 }}
            className="flex-1 flex flex-col h-full bg-gradient-to-br from-white/[0.03] to-transparent 
                      border border-white/[0.06] rounded-3xl overflow-hidden"
        >
            {/* Header */}
            <div className="px-6 py-4 border-b border-white/[0.06] bg-gradient-to-r from-cyan-500/5 via-transparent to-violet-500/5">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <motion.button
                            whileHover={{ scale: 1.05, x: -3 }}
                            whileTap={{ scale: 0.95 }}
                            onClick={onBack}
                            className="p-2 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] 
                                     rounded-xl transition-all"
                        >
                            <ChevronRight className="w-5 h-5 text-white/50 rotate-180" />
                        </motion.button>
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-gradient-to-br from-cyan-500/20 to-violet-500/10 rounded-xl">
                                <ArrowLeftRight className="w-5 h-5 text-cyan-400" />
                            </div>
                            <div>
                                <h2 className="text-lg font-semibold text-white">Swap Alternatives</h2>
                                <p className="text-xs text-white/40">
                                    {alternatives.length} alternative{alternatives.length > 1 ? 's' : ''} for "{currentProduct?.name?.substring(0, 30)}..."
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Current Product Mini */}
                    <div className="flex items-center gap-3 px-4 py-2 bg-white/[0.02] border border-white/[0.06] rounded-xl">
                        <span className="text-xs text-white/40">Current:</span>
                        <div className="w-8 h-8 bg-white/[0.05] rounded-lg overflow-hidden">
                            {currentProduct?.image_url && (
                                <img src={currentProduct.image_url} alt="" className="w-full h-full object-contain" />
                            )}
                        </div>
                        <span className="text-sm font-bold text-white">${currentProduct?.price?.toFixed(0)}</span>
                    </div>
                </div>
            </div>

            {/* Alternatives Grid */}
            <div className="flex-1 overflow-y-auto p-6 custom-scrollbar">
                <div className="grid grid-cols-2 gap-4">
                    {alternatives.map((alt, index) => {
                        const priceDiff = alt.price - currentProduct.price
                        const isCheaper = priceDiff < 0
                        const isInCart = cart.some(c => c.product_id === alt.product_id)
                        const isHovered = hoveredAlt === alt.product_id

                        return (
                            <motion.div
                                key={alt.product_id || index}
                                initial={{ y: 20, opacity: 0 }}
                                animate={{ y: 0, opacity: 1 }}
                                transition={{ delay: index * 0.1 }}
                                onMouseEnter={() => setHoveredAlt(alt.product_id)}
                                onMouseLeave={() => setHoveredAlt(null)}
                                className={`relative p-4 rounded-2xl border transition-all duration-300 cursor-pointer
                                          ${isHovered 
                                              ? 'bg-gradient-to-br from-cyan-500/10 to-violet-500/10 border-cyan-500/40 shadow-xl shadow-cyan-500/10' 
                                              : 'bg-white/[0.02] border-white/[0.06] hover:border-cyan-500/30'
                                          }`}
                            >
                                {/* Price Diff Badge */}
                                <div className={`absolute -top-2 -right-2 px-2.5 py-1 rounded-lg text-xs font-bold shadow-lg
                                               ${isCheaper 
                                                   ? 'bg-emerald-500 text-white' 
                                                   : 'bg-amber-500 text-black'
                                               }`}>
                                    {isCheaper ? `Save $${Math.abs(priceDiff).toFixed(0)}` : `+$${priceDiff.toFixed(0)}`}
                                </div>

                                <div className="flex gap-4">
                                    {/* Image */}
                                    <div className="w-24 h-24 bg-gradient-to-br from-white/[0.06] to-transparent 
                                                  rounded-xl overflow-hidden flex-shrink-0">
                                        {alt.image_url ? (
                                            <img 
                                                src={alt.image_url} 
                                                alt={alt.name}
                                                className="w-full h-full object-contain p-2"
                                            />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-2xl">📦</div>
                                        )}
                                    </div>

                                    {/* Info */}
                                    <div className="flex-1 min-w-0">
                                        {alt.brand && alt.brand !== 'Unknown' && (
                                            <p className="text-[10px] text-violet-400 font-semibold uppercase tracking-wider mb-0.5">
                                                {alt.brand}
                                            </p>
                                        )}
                                        <h4 className="text-sm text-white/90 font-medium leading-snug line-clamp-2 mb-2">
                                            {alt.name}
                                        </h4>
                                        
                                        <div className="flex items-center gap-2">
                                            {alt.rating > 0 && (
                                                <div className="flex items-center gap-1">
                                                    <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                                                    <span className="text-xs text-amber-400">{alt.rating?.toFixed(1)}</span>
                                                </div>
                                            )}
                                        </div>

                                        <p className="text-xl font-bold text-white mt-2">
                                            ${alt.price?.toFixed(2)}
                                        </p>
                                    </div>
                                </div>

                                {/* Swap Button */}
                                <motion.button
                                    whileHover={{ scale: 1.02 }}
                                    whileTap={{ scale: 0.98 }}
                                    onClick={() => onSwap(alt)}
                                    className="w-full mt-4 py-2.5 bg-gradient-to-r from-cyan-500/20 to-violet-500/20 
                                             hover:from-cyan-500/30 hover:to-violet-500/30 border border-cyan-500/30 
                                             rounded-xl text-sm font-medium text-cyan-400 flex items-center justify-center gap-2"
                                >
                                    <Replace className="w-4 h-4" />
                                    Swap to This Product
                                </motion.button>

                                {isInCart && (
                                    <div className="absolute bottom-4 right-4">
                                        <span className="px-2 py-1 bg-emerald-500/20 rounded-lg text-[9px] text-emerald-400">
                                            In Cart
                                        </span>
                                    </div>
                                )}
                            </motion.div>
                        )
                    })}
                </div>

                {alternatives.length === 0 && (
                    <div className="flex flex-col items-center justify-center py-16">
                        <Package className="w-12 h-12 text-white/10 mb-4" />
                        <p className="text-white/40">No alternatives available for this product</p>
                    </div>
                )}
            </div>
        </motion.div>
    )
}


// ============================================================================
// MODAL FOOTER
// ============================================================================
function ModalFooter({ onClose, onApply, optimized_total, savings }) {
    return (
        <motion.div 
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="relative border-t border-white/[0.06] bg-gradient-to-r from-white/[0.02] via-emerald-500/5 to-white/[0.02] 
                      backdrop-blur-xl"
        >
            <div className="px-8 py-5">
                <div className="flex items-center justify-between">
                    {/* Left - Summary */}
                    <div className="flex items-center gap-8">
                        <div>
                            <p className="text-xs text-white/40 mb-1">Optimized Total</p>
                            <p className="text-3xl font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                                ${optimized_total?.toFixed(2)}
                            </p>
                        </div>
                        {savings > 0 && (
                            <div className="flex items-center gap-2 px-4 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
                                <TrendingUp className="w-5 h-5 text-emerald-400" />
                                <div>
                                    <p className="text-lg font-bold text-emerald-400">${savings.toFixed(0)} Saved</p>
                                    <p className="text-[10px] text-emerald-400/60">vs original cart</p>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Right - Actions */}
                    <div className="flex items-center gap-4">
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={onClose}
                            className="px-8 py-3.5 bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.08] 
                                     hover:border-white/20 rounded-xl text-sm font-medium transition-all"
                        >
                            Keep Original Cart
                        </motion.button>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={onApply}
                            className="relative px-10 py-3.5 bg-gradient-to-r from-emerald-500 via-cyan-500 to-emerald-500 
                                     rounded-xl text-sm font-bold flex items-center gap-2 shadow-2xl shadow-emerald-500/30
                                     overflow-hidden group"
                        >
                            {/* Shimmer */}
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent 
                                          -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                            <Check className="w-5 h-5 relative" />
                            <span className="relative">Apply Optimized Bundle</span>
                        </motion.button>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}
