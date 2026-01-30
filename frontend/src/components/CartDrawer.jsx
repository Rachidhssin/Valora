import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
    ShoppingBag, X, Package, Sparkles, ArrowRight, ChevronRight, 
    RefreshCw, Check, Star, TrendingUp, Zap, ArrowLeftRight,
    ChevronLeft, Info, Trash2, Plus, Minus, Eye, CheckCircle2,
    Target, DollarSign, ShoppingCart, ArrowUpRight, Loader2,
    Layers, Replace, Heart, BadgePercent
} from 'lucide-react'

/**
 * MODERN CART DRAWER - Split Panel Design
 * 
 * Features:
 * - Split panel: Cart items (left) + Detail/Optimization panel (right)
 * - Tab-based navigation for different views
 * - Inline product alternatives carousel
 * - Visual budget tracker with animated bar
 * - Compare & Swap UI for bundle optimization
 */

// ============================================================================
// MAIN CART DRAWER COMPONENT
// ============================================================================
export default function CartDrawer({ 
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
    const [activeTab, setActiveTab] = useState('cart') // 'cart' | 'optimize'
    const [selectedProduct, setSelectedProduct] = useState(null)
    const [compareMode, setCompareMode] = useState(false)
    const [selectedForCompare, setSelectedForCompare] = useState([])
    
    const budgetPercent = Math.min((cartTotal / budget) * 100, 100)
    const isOverBudget = cartTotal > budget
    const remainingBudget = budget - cartTotal
    const savings = optimizationResult ? Math.max(0, budget - (optimizationResult.optimized_total || 0)) : 0

    // Auto-switch to optimize tab when results arrive
    useEffect(() => {
        if (optimizationResult) {
            setActiveTab('optimize')
        }
    }, [optimizationResult])

    // Handle product swaps
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
            setActiveTab('cart')
        }
    }

    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
                    />
                    
                    {/* Drawer */}
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                        className="fixed top-0 right-0 bottom-0 w-full max-w-4xl z-50 flex"
                    >
                        {/* Main Cart Panel */}
                        <div className="flex-1 flex flex-col bg-gradient-to-b from-[#0d0d12] to-[#08080c] 
                                      border-l border-white/[0.06] overflow-hidden">
                            
                            {/* Header with Tabs */}
                            <CartHeader 
                                cart={cart}
                                activeTab={activeTab}
                                setActiveTab={setActiveTab}
                                optimizationResult={optimizationResult}
                                onClose={onClose}
                            />

                            {/* Budget Bar - Always visible */}
                            <BudgetTracker 
                                cartTotal={cartTotal}
                                budget={budget}
                                budgetPercent={budgetPercent}
                                isOverBudget={isOverBudget}
                                remainingBudget={remainingBudget}
                                optimizedTotal={optimizationResult?.optimized_total}
                                activeTab={activeTab}
                            />

                            {/* Main Content Area */}
                            <div className="flex-1 overflow-hidden flex flex-col">
                                <AnimatePresence mode="wait">
                                    {activeTab === 'cart' ? (
                                        <CartTabContent
                                            key="cart-tab"
                                            cart={cart}
                                            onRemove={onRemove}
                                            onClose={onClose}
                                            selectedProduct={selectedProduct}
                                            setSelectedProduct={setSelectedProduct}
                                        />
                                    ) : (
                                        <OptimizeTabContent
                                            key="optimize-tab"
                                            optimizationResult={optimizationResult}
                                            handleSwap={handleSwap}
                                            setSelectedProduct={setSelectedProduct}
                                            cart={cart}
                                            addToCart={addToCart}
                                            userId={userId}
                                        />
                                    )}
                                </AnimatePresence>
                            </div>

                            {/* Footer Actions */}
                            <CartFooter 
                                cart={cart}
                                cartTotal={cartTotal}
                                activeTab={activeTab}
                                isOverBudget={isOverBudget}
                                isOptimizing={isOptimizing}
                                onClear={onClear}
                                onOptimize={onOptimize}
                                optimizationResult={optimizationResult}
                                applyOptimizedBundle={applyOptimizedBundle}
                                setOptimizationResult={setOptimizationResult}
                                setActiveTab={setActiveTab}
                            />
                        </div>

                        {/* Right Panel - Product Details (slides in when product selected) */}
                        <AnimatePresence>
                            {selectedProduct && (
                                <ProductDetailPanel 
                                    product={selectedProduct}
                                    onClose={() => setSelectedProduct(null)}
                                    cart={cart}
                                    addToCart={addToCart}
                                />
                            )}
                        </AnimatePresence>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}


// ============================================================================
// CART HEADER WITH TABS
// ============================================================================
function CartHeader({ cart, activeTab, setActiveTab, optimizationResult, onClose }) {
    return (
        <div className="relative border-b border-white/[0.06]">
            {/* Background glow */}
            <div className="absolute inset-0 bg-gradient-to-r from-violet-600/5 via-transparent to-cyan-600/5" />
            
            <div className="relative px-6 pt-5 pb-4">
                {/* Title Row */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                        <div className="relative">
                            <div className="p-3 bg-gradient-to-br from-violet-500/20 to-purple-600/10 
                                          rounded-2xl border border-violet-500/20">
                                <ShoppingCart className="w-6 h-6 text-violet-400" />
                            </div>
                            {cart.length > 0 && (
                                <motion.div 
                                    initial={{ scale: 0 }}
                                    animate={{ scale: 1 }}
                                    className="absolute -top-1 -right-1 w-6 h-6 bg-gradient-to-r from-violet-500 to-purple-500 
                                             rounded-full flex items-center justify-center text-xs font-bold shadow-lg"
                                >
                                    {cart.length}
                                </motion.div>
                            )}
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Shopping Cart</h2>
                            <p className="text-sm text-white/40">
                                {cart.length === 0 ? 'Start adding products' : `${cart.length} item${cart.length > 1 ? 's' : ''}`}
                            </p>
                        </div>
                    </div>
                    
                    <motion.button 
                        whileHover={{ scale: 1.1, rotate: 90 }}
                        whileTap={{ scale: 0.9 }}
                        onClick={onClose}
                        className="p-2.5 hover:bg-white/[0.05] rounded-xl transition-colors"
                    >
                        <X className="w-5 h-5 text-white/50" />
                    </motion.button>
                </div>

                {/* Tab Navigation */}
                {cart.length > 0 && (
                    <div className="flex gap-2 p-1 bg-white/[0.03] rounded-xl border border-white/[0.06]">
                        <TabButton 
                            active={activeTab === 'cart'}
                            onClick={() => setActiveTab('cart')}
                            icon={<ShoppingBag className="w-4 h-4" />}
                            label="Your Cart"
                        />
                        <TabButton 
                            active={activeTab === 'optimize'}
                            onClick={() => setActiveTab('optimize')}
                            icon={<Sparkles className="w-4 h-4" />}
                            label="AI Bundle"
                            badge={optimizationResult ? '✓' : null}
                            badgeColor="bg-emerald-500"
                        />
                    </div>
                )}
            </div>
        </div>
    )
}

function TabButton({ active, onClick, icon, label, badge, badgeColor }) {
    return (
        <button
            onClick={onClick}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg 
                       text-sm font-medium transition-all relative
                       ${active 
                           ? 'bg-gradient-to-r from-violet-500/20 to-purple-500/20 text-white border border-violet-500/30' 
                           : 'text-white/50 hover:text-white/80 hover:bg-white/[0.03]'
                       }`}
        >
            {icon}
            {label}
            {badge && (
                <span className={`w-5 h-5 ${badgeColor} rounded-full flex items-center justify-center text-[10px] font-bold`}>
                    {badge}
                </span>
            )}
        </button>
    )
}


// ============================================================================
// BUDGET TRACKER - Animated progress bar with comparison
// ============================================================================
function BudgetTracker({ cartTotal, budget, budgetPercent, isOverBudget, remainingBudget, optimizedTotal, activeTab }) {
    const optimizedPercent = optimizedTotal ? Math.min((optimizedTotal / budget) * 100, 100) : 0
    const showComparison = activeTab === 'optimize' && optimizedTotal !== undefined

    return (
        <div className="px-6 py-4 bg-gradient-to-r from-white/[0.02] to-transparent border-b border-white/[0.04]">
            {/* Labels */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    <div className={`w-2.5 h-2.5 rounded-full ${isOverBudget ? 'bg-red-500 animate-pulse' : 'bg-emerald-500'}`} />
                    <span className="text-sm text-white/60">Budget Progress</span>
                </div>
                <div className="flex items-center gap-4">
                    {showComparison && (
                        <div className="flex items-center gap-2 px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg">
                            <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-xs text-emerald-400 font-medium">
                                Save ${(cartTotal - optimizedTotal).toFixed(0)}
                            </span>
                        </div>
                    )}
                    <div className="text-right">
                        <span className={`text-base font-bold ${isOverBudget ? 'text-red-400' : 'text-white'}`}>
                            ${(showComparison ? optimizedTotal : cartTotal).toFixed(2)}
                        </span>
                        <span className="text-sm text-white/30"> / ${budget}</span>
                    </div>
                </div>
            </div>
            
            {/* Progress Bar with dual indicator */}
            <div className="relative h-3 bg-white/[0.05] rounded-full overflow-hidden">
                {/* Current cart (ghost when optimized showing) */}
                {showComparison && (
                    <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${budgetPercent}%` }}
                        className="absolute h-full bg-white/10 rounded-full"
                    />
                )}
                
                {/* Main progress */}
                <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${showComparison ? optimizedPercent : budgetPercent}%` }}
                    transition={{ duration: 0.6, ease: 'easeOut' }}
                    className={`absolute h-full rounded-full ${
                        showComparison 
                            ? 'bg-gradient-to-r from-emerald-500 via-cyan-500 to-emerald-400'
                            : isOverBudget 
                                ? 'bg-gradient-to-r from-red-500 via-orange-500 to-red-400' 
                                : 'bg-gradient-to-r from-violet-500 via-purple-500 to-violet-400'
                    }`}
                >
                    {/* Shimmer */}
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
                </motion.div>
                
                {/* Markers */}
                <div className="absolute right-0 top-0 bottom-0 w-px bg-white/20" />
            </div>

            {/* Bottom labels */}
            <div className="flex justify-between mt-2 text-[11px]">
                <span className="text-white/30">$0</span>
                <span className={`font-medium ${isOverBudget ? 'text-red-400' : 'text-emerald-400'}`}>
                    {isOverBudget 
                        ? `$${Math.abs(remainingBudget).toFixed(0)} over` 
                        : `$${remainingBudget.toFixed(0)} remaining`
                    }
                </span>
                <span className="text-white/30">${budget}</span>
            </div>
        </div>
    )
}


// ============================================================================
// CART TAB CONTENT
// ============================================================================
function CartTabContent({ cart, onRemove, onClose, selectedProduct, setSelectedProduct }) {
    if (cart.length === 0) {
        return (
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="flex-1 flex items-center justify-center p-8"
            >
                <div className="text-center max-w-sm">
                    <motion.div 
                        animate={{ y: [0, -10, 0] }}
                        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
                        className="relative w-32 h-32 mx-auto mb-8"
                    >
                        <div className="absolute inset-0 bg-gradient-to-br from-violet-500/20 to-cyan-500/20 rounded-full blur-2xl" />
                        <div className="absolute inset-4 bg-gradient-to-br from-white/[0.03] to-transparent 
                                      rounded-full flex items-center justify-center border border-white/[0.08]">
                            <ShoppingBag className="w-12 h-12 text-white/20" />
                        </div>
                    </motion.div>
                    <h3 className="text-xl font-bold text-white/80 mb-3">Your cart is empty</h3>
                    <p className="text-sm text-white/40 mb-8 leading-relaxed">
                        Browse our collection and add products to start building your perfect bundle
                    </p>
                    <motion.button 
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={onClose}
                        className="px-8 py-3 bg-gradient-to-r from-violet-500/20 to-purple-500/20 
                                 border border-violet-500/30 hover:border-violet-500/50
                                 rounded-xl text-sm font-medium text-violet-300 transition-all"
                    >
                        Start Shopping
                    </motion.button>
                </div>
            </motion.div>
        )
    }

    return (
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar"
        >
            <AnimatePresence>
                {cart.map((item, index) => (
                    <CartItemCard 
                        key={item.product_id || index}
                        item={item}
                        index={index}
                        onRemove={onRemove}
                        isSelected={selectedProduct?.product_id === item.product_id}
                        onSelect={() => setSelectedProduct(
                            selectedProduct?.product_id === item.product_id ? null : item
                        )}
                    />
                ))}
            </AnimatePresence>
        </motion.div>
    )
}


// ============================================================================
// CART ITEM CARD - Compact, informative, with quick actions
// ============================================================================
function CartItemCard({ item, index, onRemove, isSelected, onSelect }) {
    const [isHovered, setIsHovered] = useState(false)

    return (
        <motion.div
            layout
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, x: -100, scale: 0.9 }}
            transition={{ delay: index * 0.05 }}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            onClick={onSelect}
            className={`relative rounded-2xl overflow-hidden cursor-pointer transition-all
                       ${isSelected 
                           ? 'bg-gradient-to-r from-violet-500/10 to-purple-500/5 border-2 border-violet-500/40' 
                           : 'bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/[0.06] hover:border-violet-500/30'
                       }`}
        >
            <div className="flex gap-4 p-4">
                {/* Product Image */}
                <div className="relative w-20 h-20 bg-gradient-to-br from-white/[0.06] to-transparent 
                              rounded-xl overflow-hidden flex-shrink-0 group">
                    {item.image_url ? (
                        <img
                            src={item.image_url}
                            alt={item.name}
                            className="w-full h-full object-contain p-2 transition-transform group-hover:scale-110"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-2xl">📦</div>
                    )}
                    
                    {/* Index Badge */}
                    <div className="absolute bottom-1 left-1 w-6 h-6 bg-violet-500/90 backdrop-blur-sm 
                                  rounded-lg flex items-center justify-center text-[10px] font-bold text-white shadow-lg">
                        {index + 1}
                    </div>
                </div>

                {/* Product Info */}
                <div className="flex-1 min-w-0 py-0.5">
                    {item.brand && item.brand !== 'Unknown' && (
                        <p className="text-[10px] text-violet-400 font-semibold uppercase tracking-wider mb-0.5">
                            {item.brand}
                        </p>
                    )}
                    
                    <h4 className="text-sm text-white/90 line-clamp-2 font-medium leading-snug mb-2">
                        {item.name}
                    </h4>
                    
                    <div className="flex items-center gap-2 flex-wrap">
                        {item.category && (
                            <span className="px-2 py-0.5 bg-white/[0.05] border border-white/[0.08] 
                                           rounded text-[9px] text-white/40 uppercase">
                                {item.category.split(',')[0]}
                            </span>
                        )}
                        {item.rating > 0 && (
                            <span className="flex items-center gap-1 text-[10px] text-amber-400">
                                <Star className="w-3 h-3 fill-amber-400" />
                                {item.rating?.toFixed(1)}
                            </span>
                        )}
                    </div>
                </div>

                {/* Price & Actions */}
                <div className="flex flex-col items-end justify-between">
                    <AnimatePresence mode="wait">
                        {isHovered ? (
                            <motion.button
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                                whileHover={{ scale: 1.1 }}
                                whileTap={{ scale: 0.9 }}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onRemove(item.product_id)
                                }}
                                className="p-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-all"
                            >
                                <Trash2 className="w-4 h-4" />
                            </motion.button>
                        ) : (
                            <motion.button
                                initial={{ opacity: 0, scale: 0.8 }}
                                animate={{ opacity: 1, scale: 1 }}
                                exit={{ opacity: 0, scale: 0.8 }}
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onSelect()
                                }}
                                className="p-2 text-white/30 hover:text-white/60 rounded-lg transition-all"
                            >
                                <Eye className="w-4 h-4" />
                            </motion.button>
                        )}
                    </AnimatePresence>
                    
                    <p className="text-lg font-bold bg-gradient-to-r from-violet-400 to-purple-400 bg-clip-text text-transparent">
                        ${item.price?.toFixed(2)}
                    </p>
                </div>
            </div>

            {/* Selection indicator */}
            {isSelected && (
                <motion.div 
                    layoutId="selected-indicator"
                    className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-violet-500 to-purple-500"
                />
            )}
        </motion.div>
    )
}


// ============================================================================
// OPTIMIZE TAB CONTENT - Bundle results with comparison view
// ============================================================================
function OptimizeTabContent({ optimizationResult, handleSwap, setSelectedProduct, cart, addToCart, userId }) {
    if (!optimizationResult) {
        return (
            <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className="flex-1 flex items-center justify-center p-8"
            >
                <div className="text-center max-w-sm">
                    <div className="relative w-28 h-28 mx-auto mb-6">
                        <div className="absolute inset-0 bg-gradient-to-br from-cyan-500/20 to-violet-500/20 rounded-full blur-2xl animate-pulse" />
                        <div className="absolute inset-4 bg-gradient-to-br from-white/[0.03] to-transparent 
                                      rounded-full flex items-center justify-center border border-white/[0.08]">
                            <Sparkles className="w-10 h-10 text-cyan-400/50" />
                        </div>
                    </div>
                    <h3 className="text-lg font-bold text-white/70 mb-2">No optimization yet</h3>
                    <p className="text-sm text-white/40 leading-relaxed">
                        Click "Optimize Bundle" to let AI find the best combination of products for your budget
                    </p>
                </div>
            </motion.div>
        )
    }

    return (
        <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex-1 overflow-y-auto custom-scrollbar"
        >
            {/* Success Header */}
            <div className="p-6 bg-gradient-to-r from-emerald-500/10 via-cyan-500/5 to-transparent border-b border-white/[0.06]">
                <motion.div 
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex items-center gap-4"
                >
                    <div className="p-3 bg-gradient-to-br from-emerald-500 to-cyan-500 rounded-2xl shadow-lg shadow-emerald-500/30">
                        <Check className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-white">Perfect Bundle Found!</h3>
                        <p className="text-sm text-white/50">
                            {optimizationResult.optimized_products?.length} products optimized for your ${optimizationResult.optimized_total?.toFixed(0)} budget
                        </p>
                    </div>
                </motion.div>

                {/* Quick Stats */}
                <div className="grid grid-cols-3 gap-3 mt-5">
                    <StatCard 
                        icon={<DollarSign className="w-4 h-4" />}
                        label="Total Cost"
                        value={`$${optimizationResult.optimized_total?.toFixed(0)}`}
                        color="violet"
                    />
                    <StatCard 
                        icon={<Package className="w-4 h-4" />}
                        label="Products"
                        value={optimizationResult.optimized_products?.length || 0}
                        color="cyan"
                    />
                    <StatCard 
                        icon={<TrendingUp className="w-4 h-4" />}
                        label="Saved"
                        value={`$${Math.max(0, cart.reduce((s,p) => s + p.price, 0) - optimizationResult.optimized_total).toFixed(0)}`}
                        color="emerald"
                    />
                </div>
            </div>

            {/* Products List */}
            <div className="p-4 space-y-4">
                <div className="flex items-center justify-between px-2">
                    <span className="text-xs text-white/40 uppercase tracking-wider flex items-center gap-2">
                        <Layers className="w-3.5 h-3.5" />
                        Optimized Products
                    </span>
                    <span className="text-[10px] text-cyan-400/60 flex items-center gap-1">
                        <RefreshCw className="w-3 h-3" />
                        Click cards for alternatives
                    </span>
                </div>

                {optimizationResult.optimized_products?.map((item, i) => (
                    <OptimizedProductCard
                        key={item.product_id || i}
                        item={{...item, slot_id: item.slot_id || `suggestion_${i}`}}
                        index={i}
                        alternatives={optimizationResult.alternatives?.[item.slot_id || `suggestion_${i}`] || []}
                        onSwap={handleSwap}
                        onViewDetails={setSelectedProduct}
                        cart={cart}
                        addToCart={addToCart}
                    />
                ))}
            </div>
        </motion.div>
    )
}

function StatCard({ icon, label, value, color }) {
    const colors = {
        violet: 'from-violet-500/20 to-violet-500/5 border-violet-500/30 text-violet-400',
        cyan: 'from-cyan-500/20 to-cyan-500/5 border-cyan-500/30 text-cyan-400',
        emerald: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30 text-emerald-400'
    }
    
    return (
        <div className={`p-3 bg-gradient-to-br ${colors[color]} border rounded-xl`}>
            <div className="flex items-center gap-1.5 text-xs opacity-70 mb-1">
                {icon}
                {label}
            </div>
            <p className="text-xl font-bold">{value}</p>
        </div>
    )
}


// ============================================================================
// OPTIMIZED PRODUCT CARD - With inline alternatives carousel
// ============================================================================
function OptimizedProductCard({ item, index, alternatives, onSwap, onViewDetails, cart, addToCart }) {
    const [showAlternatives, setShowAlternatives] = useState(false)
    const isInCart = cart.some(c => c.product_id === item.product_id)
    const isFromCart = !item.is_suggestion

    const handleAddToCart = (e, product) => {
        e.stopPropagation()
        // Trigger animation
        const rect = e.currentTarget.getBoundingClientRect()
        window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
            detail: {
                x: rect.left + rect.width / 2,
                y: rect.top + rect.height / 2,
                productImage: product.image_url,
                productName: product.name,
                productPrice: product.price
            }
        }))
        addToCart(product)
    }

    return (
        <motion.div
            layout
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1 + index * 0.1 }}
            className="rounded-2xl overflow-hidden"
        >
            {/* Main Card */}
            <motion.div 
                onClick={() => alternatives.length > 0 && setShowAlternatives(!showAlternatives)}
                className={`relative p-4 cursor-pointer transition-all
                          ${showAlternatives 
                              ? 'bg-gradient-to-r from-cyan-500/10 to-violet-500/10 border-2 border-cyan-500/40' 
                              : 'bg-gradient-to-br from-white/[0.04] to-white/[0.01] border border-white/[0.08] hover:border-violet-500/30'
                          }`}
            >
                <div className="flex gap-4">
                    {/* Product Image */}
                    <div className="relative w-24 h-24 bg-gradient-to-br from-white/[0.06] to-transparent 
                                  rounded-xl overflow-hidden flex-shrink-0">
                        {item.image_url ? (
                            <img 
                                src={item.image_url} 
                                alt={item.name}
                                className="w-full h-full object-contain p-2"
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center text-2xl">📦</div>
                        )}
                        
                        {/* Number Badge */}
                        <div className="absolute top-1 left-1 w-6 h-6 bg-gradient-to-br from-violet-500 to-purple-600 
                                      rounded-lg flex items-center justify-center text-[10px] font-bold shadow-lg">
                            {index + 1}
                        </div>
                    </div>

                    {/* Product Info */}
                    <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-1">
                            <div className="flex items-center gap-2 flex-wrap">
                                {isFromCart && (
                                    <span className="px-2 py-0.5 bg-emerald-500/20 border border-emerald-500/30 
                                                   rounded text-[9px] text-emerald-400 uppercase font-medium">
                                        From Cart
                                    </span>
                                )}
                                {item.brand && item.brand !== 'Unknown' && (
                                    <span className="text-[10px] text-violet-400 font-semibold uppercase">
                                        {item.brand}
                                    </span>
                                )}
                            </div>
                            <p className="text-lg font-bold bg-gradient-to-r from-violet-400 to-purple-400 
                                        bg-clip-text text-transparent whitespace-nowrap">
                                ${item.price?.toFixed(2)}
                            </p>
                        </div>
                        
                        <h4 className="text-sm text-white/90 font-medium leading-snug mb-2 line-clamp-2">
                            {item.name}
                        </h4>

                        {/* Action Row */}
                        <div className="flex items-center gap-2">
                            {alternatives.length > 0 && (
                                <button className="flex items-center gap-1.5 px-2.5 py-1 bg-cyan-500/10 
                                                 border border-cyan-500/30 rounded-lg text-[10px] text-cyan-400 
                                                 hover:bg-cyan-500/20 transition-all">
                                    <ArrowLeftRight className="w-3 h-3" />
                                    {alternatives.length} alternatives
                                    <ChevronRight className={`w-3 h-3 transition-transform ${showAlternatives ? 'rotate-90' : ''}`} />
                                </button>
                            )}
                            
                            {!isInCart && item.is_suggestion && (
                                <motion.button
                                    whileHover={{ scale: 1.05 }}
                                    whileTap={{ scale: 0.95 }}
                                    onClick={(e) => handleAddToCart(e, item)}
                                    className="flex items-center gap-1.5 px-2.5 py-1 bg-violet-500/20 
                                             border border-violet-500/30 rounded-lg text-[10px] text-violet-400 
                                             hover:bg-violet-500/30 transition-all"
                                >
                                    <Plus className="w-3 h-3" />
                                    Add to Cart
                                </motion.button>
                            )}
                            
                            {isInCart && (
                                <span className="flex items-center gap-1 text-[10px] text-emerald-400">
                                    <CheckCircle2 className="w-3 h-3" />
                                    In cart
                                </span>
                            )}

                            <button
                                onClick={(e) => {
                                    e.stopPropagation()
                                    onViewDetails(item)
                                }}
                                className="ml-auto p-1.5 text-white/30 hover:text-white/60 
                                         hover:bg-white/[0.05] rounded-lg transition-all"
                            >
                                <Info className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                </div>
            </motion.div>

            {/* Alternatives Carousel */}
            <AnimatePresence>
                {showAlternatives && alternatives.length > 0 && (
                    <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                    >
                        <div className="p-3 bg-gradient-to-b from-white/[0.02] to-transparent border-x border-b 
                                      border-white/[0.06] rounded-b-2xl">
                            <p className="text-[10px] text-white/40 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <Replace className="w-3 h-3" />
                                Swap with alternative
                            </p>
                            
                            <div className="flex gap-3 overflow-x-auto pb-2 custom-scrollbar-horizontal">
                                {alternatives.map((alt, ai) => (
                                    <AlternativeCard 
                                        key={alt.product_id || ai}
                                        alt={alt}
                                        currentPrice={item.price}
                                        onSwap={() => onSwap(index, alt)}
                                    />
                                ))}
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}


// ============================================================================
// ALTERNATIVE CARD - Compact card for swapping
// ============================================================================
function AlternativeCard({ alt, currentPrice, onSwap }) {
    const priceDiff = alt.price - currentPrice
    const isCheaper = priceDiff < 0

    return (
        <motion.button
            whileHover={{ scale: 1.02, y: -2 }}
            whileTap={{ scale: 0.98 }}
            onClick={onSwap}
            className="flex-shrink-0 w-48 p-3 bg-gradient-to-br from-white/[0.04] to-white/[0.01] 
                     border border-white/[0.08] hover:border-cyan-500/40 rounded-xl 
                     transition-all text-left group"
        >
            <div className="flex gap-3">
                <div className="w-14 h-14 bg-gradient-to-br from-white/[0.06] to-transparent 
                              rounded-lg overflow-hidden flex-shrink-0">
                    {alt.image_url ? (
                        <img 
                            src={alt.image_url} 
                            alt={alt.name}
                            className="w-full h-full object-contain p-1"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-lg">📦</div>
                    )}
                </div>
                
                <div className="flex-1 min-w-0">
                    <p className="text-[10px] text-white/60 line-clamp-2 mb-1.5">{alt.name}</p>
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-bold text-white">${alt.price?.toFixed(0)}</span>
                        <span className={`text-[10px] ${isCheaper ? 'text-emerald-400' : 'text-amber-400'}`}>
                            {isCheaper ? `−$${Math.abs(priceDiff).toFixed(0)}` : `+$${priceDiff.toFixed(0)}`}
                        </span>
                    </div>
                </div>
            </div>
            
            {/* Swap indicator */}
            <div className="mt-2 py-1.5 bg-cyan-500/10 border border-cyan-500/20 rounded-lg 
                          text-[10px] text-cyan-400 text-center opacity-0 group-hover:opacity-100 transition-opacity">
                Click to swap
            </div>
        </motion.button>
    )
}


// ============================================================================
// PRODUCT DETAIL PANEL - Slide-in panel for product info
// ============================================================================
function ProductDetailPanel({ product, onClose, cart, addToCart }) {
    const isInCart = cart.some(c => c.product_id === product.product_id)

    const handleAddToCart = () => {
        window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
            detail: {
                x: window.innerWidth - 300,
                y: 300,
                productImage: product.image_url,
                productName: product.name,
                productPrice: product.price
            }
        }))
        addToCart(product)
        onClose()
    }

    return (
        <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 320, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            className="bg-gradient-to-b from-[#0a0a0f] to-[#06060a] border-l border-white/[0.08] 
                     overflow-hidden flex flex-col"
        >
            <div className="p-4 overflow-y-auto custom-scrollbar flex-1">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <span className="text-xs text-white/40 uppercase tracking-wider">Product Details</span>
                    <button 
                        onClick={onClose}
                        className="p-1.5 hover:bg-white/[0.05] rounded-lg transition-colors"
                    >
                        <X className="w-4 h-4 text-white/40" />
                    </button>
                </div>

                {/* Product Image */}
                <div className="relative aspect-square bg-gradient-to-br from-white/[0.04] to-transparent 
                              rounded-2xl overflow-hidden mb-4">
                    {product.image_url ? (
                        <img 
                            src={product.image_url} 
                            alt={product.name}
                            className="w-full h-full object-contain p-4"
                        />
                    ) : (
                        <div className="w-full h-full flex items-center justify-center text-5xl">📦</div>
                    )}
                </div>

                {/* Brand & Category */}
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                    {product.brand && product.brand !== 'Unknown' && (
                        <span className="px-2.5 py-1 bg-violet-500/10 border border-violet-500/20 
                                       rounded-lg text-xs text-violet-400 font-medium">
                            {product.brand}
                        </span>
                    )}
                    {product.category && (
                        <span className="px-2.5 py-1 bg-white/[0.05] border border-white/[0.08] 
                                       rounded-lg text-xs text-white/40">
                            {product.category.split(',')[0]}
                        </span>
                    )}
                </div>

                {/* Name */}
                <h3 className="text-lg font-bold text-white/95 leading-snug mb-3">
                    {product.name}
                </h3>

                {/* Price */}
                <p className="text-3xl font-bold bg-gradient-to-r from-violet-400 via-purple-400 to-pink-400 
                            bg-clip-text text-transparent mb-4">
                    ${product.price?.toFixed(2)}
                </p>

                {/* Stats */}
                <div className="grid grid-cols-2 gap-2 mb-4">
                    {product.rating > 0 && (
                        <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.06]">
                            <div className="flex items-center gap-1.5 text-amber-400 mb-1">
                                <Star className="w-4 h-4 fill-amber-400" />
                                <span className="text-sm font-bold">{product.rating?.toFixed(1)}</span>
                            </div>
                            <p className="text-[10px] text-white/40">Rating</p>
                        </div>
                    )}
                    {product.review_count > 0 && (
                        <div className="p-3 bg-white/[0.03] rounded-xl border border-white/[0.06]">
                            <p className="text-sm font-bold text-white/80 mb-1">{product.review_count}</p>
                            <p className="text-[10px] text-white/40">Reviews</p>
                        </div>
                    )}
                </div>

                {/* Description if available */}
                {product.description && (
                    <div className="p-3 bg-white/[0.02] rounded-xl border border-white/[0.05] mb-4">
                        <p className="text-xs text-white/50 leading-relaxed line-clamp-4">
                            {product.description}
                        </p>
                    </div>
                )}
            </div>

            {/* Action Button */}
            <div className="p-4 border-t border-white/[0.06]">
                {isInCart ? (
                    <div className="flex items-center justify-center gap-2 py-3 bg-emerald-500/10 
                                  border border-emerald-500/20 rounded-xl">
                        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                        <span className="text-sm text-emerald-400 font-medium">Already in your cart</span>
                    </div>
                ) : (
                    <motion.button
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        onClick={handleAddToCart}
                        className="w-full py-3 bg-gradient-to-r from-violet-500 to-purple-500 
                                 hover:from-violet-600 hover:to-purple-600 rounded-xl text-sm font-semibold 
                                 flex items-center justify-center gap-2 shadow-lg shadow-violet-500/30"
                    >
                        <Plus className="w-4 h-4" />
                        Add to Cart
                    </motion.button>
                )}
            </div>
        </motion.div>
    )
}


// ============================================================================
// CART FOOTER - Actions and summary
// ============================================================================
function CartFooter({ 
    cart, cartTotal, activeTab, isOverBudget, isOptimizing, 
    onClear, onOptimize, optimizationResult, applyOptimizedBundle,
    setOptimizationResult, setActiveTab
}) {
    if (cart.length === 0) return null

    return (
        <div className="relative p-5 border-t border-white/[0.06] bg-[#0a0a0f]/95 backdrop-blur-xl">
            {/* Summary Row */}
            <div className="flex items-end justify-between mb-4">
                <div>
                    <p className="text-xs text-white/40 mb-1">
                        {activeTab === 'optimize' && optimizationResult ? 'Optimized Total' : 'Cart Total'}
                    </p>
                    <p className={`text-2xl font-bold ${isOverBudget && activeTab === 'cart' ? 'text-red-400' : 'text-white'}`}>
                        ${activeTab === 'optimize' && optimizationResult 
                            ? optimizationResult.optimized_total?.toFixed(2) 
                            : cartTotal.toFixed(2)
                        }
                    </p>
                </div>
                <div className="text-right">
                    <p className="text-xs text-white/40 mb-1">{cart.length} items</p>
                    <p className={`text-sm font-medium ${isOverBudget && activeTab === 'cart' ? 'text-red-400' : 'text-emerald-400'}`}>
                        {isOverBudget && activeTab === 'cart' ? 'Over budget' : 'Within budget ✓'}
                    </p>
                </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
                {activeTab === 'cart' ? (
                    <>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={onClear}
                            className="flex-1 py-3 bg-white/[0.03] hover:bg-red-500/10 
                                     border border-white/[0.08] hover:border-red-500/30
                                     rounded-xl text-sm font-medium transition-all text-white/60 hover:text-red-400"
                        >
                            Clear All
                        </motion.button>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={onOptimize}
                            disabled={isOptimizing}
                            className="flex-[2] py-3 bg-gradient-to-r from-violet-500 via-purple-500 to-violet-600 
                                     hover:from-violet-600 hover:via-purple-600 hover:to-violet-700 
                                     rounded-xl text-sm font-semibold transition-all 
                                     flex items-center justify-center gap-2
                                     disabled:opacity-50 shadow-lg shadow-violet-500/30 relative overflow-hidden group"
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent 
                                          -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                            
                            {isOptimizing ? (
                                <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>Finding Best Bundle...</span>
                                </>
                            ) : (
                                <>
                                    <Sparkles className="w-4 h-4" />
                                    <span>Optimize Bundle</span>
                                </>
                            )}
                        </motion.button>
                    </>
                ) : (
                    <>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => {
                                setOptimizationResult(null)
                                setActiveTab('cart')
                            }}
                            className="flex-1 py-3 bg-white/[0.03] hover:bg-white/[0.06] 
                                     border border-white/[0.08] hover:border-white/20
                                     rounded-xl text-sm font-medium transition-all"
                        >
                            Keep Current Cart
                        </motion.button>
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={applyOptimizedBundle}
                            className="flex-[2] py-3 bg-gradient-to-r from-emerald-500 via-cyan-500 to-emerald-600 
                                     hover:from-emerald-600 hover:via-cyan-600 hover:to-emerald-700 
                                     rounded-xl text-sm font-semibold transition-all 
                                     flex items-center justify-center gap-2
                                     shadow-lg shadow-emerald-500/30 relative overflow-hidden group"
                        >
                            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent 
                                          -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
                            <Check className="w-4 h-4" />
                            <span>Apply Optimized Bundle</span>
                        </motion.button>
                    </>
                )}
            </div>

            {/* Hint */}
            <p className="text-[10px] text-center text-white/30 mt-3">
                {activeTab === 'cart' 
                    ? 'AI will find complementary products that maximize value within your budget'
                    : 'Click items to see alternatives or view product details'
                }
            </p>
        </div>
    )
}
