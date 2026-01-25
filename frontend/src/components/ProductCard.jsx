import { useState } from 'react'
import { motion } from 'framer-motion'
import { ShoppingCart, Check, Star, Info, ExternalLink } from 'lucide-react'
import { useStore } from '../store/useStore'
import ConfidenceBadge, { BudgetFitBadge } from './ConfidenceBadge'

/**
 * ProductCard - Enhanced product display with confidence badges and animations
 * 
 * Features:
 * - Lazy loaded image with hover zoom
 * - Confidence badge (match %)
 * - Budget fit indicator
 * - "Why recommended" tooltip
 * - Add to cart with micro-animation
 */
export default function ProductCard({ product, onSelect }) {
    const [isAdding, setIsAdding] = useState(false)
    const [isAdded, setIsAdded] = useState(false)
    const [showTooltip, setShowTooltip] = useState(false)

    const { addToCart, budget, cart } = useStore()

    const isInCart = cart.some(item => item.product_id === product.product_id)

    // Extract product data with fallbacks
    const {
        product_id,
        name = 'Unknown Product',
        price = 0,
        rating = 0,
        rating_count = 0,
        category = 'Unknown',
        brand = 'Unknown',
        image_url = '',
        score = 0.75, // Confidence score from search
        description = '',
    } = product

    const handleAddToCart = async (e) => {
        e.stopPropagation()
        if (isInCart || isAdding) return

        setIsAdding(true)

        // Simulate adding animation
        await new Promise(resolve => setTimeout(resolve, 300))

        addToCart({
            product_id,
            name,
            price,
            category,
            brand,
            image_url
        })

        setIsAdding(false)
        setIsAdded(true)

        // Reset added state after animation
        setTimeout(() => setIsAdded(false), 2000)
    }

    return (
        <motion.div
            className="group relative bg-white/5 border border-white/10 rounded-2xl overflow-hidden
                       hover:border-primary-500/30 hover:bg-white/[0.07] transition-all cursor-pointer"
            whileHover={{ y: -4 }}
            onClick={() => onSelect?.(product)}
            layout
        >
            {/* Image Container */}
            <div className="relative aspect-square overflow-hidden bg-white/5">
                {image_url ? (
                    <motion.img
                        src={image_url}
                        alt={name}
                        className="w-full h-full object-contain p-4"
                        loading="lazy"
                        whileHover={{ scale: 1.08 }}
                        transition={{ duration: 0.3 }}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-white/20 text-4xl">
                        📦
                    </div>
                )}

                {/* Confidence Badge - Top Right */}
                {score > 0 && (
                    <div className="absolute top-3 right-3">
                        <ConfidenceBadge score={score} size="sm" />
                    </div>
                )}

                {/* Category Badge - Top Left */}
                <div className="absolute top-3 left-3">
                    <span className="px-2 py-1 bg-black/50 backdrop-blur-sm text-white/80 
                                   text-xs rounded-full">
                        {category}
                    </span>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 space-y-3">
                {/* Brand */}
                <p className="text-xs text-primary-400 font-medium uppercase tracking-wide">
                    {brand}
                </p>

                {/* Title */}
                <h3 className="text-sm font-medium text-white/90 line-clamp-2 min-h-[2.5rem]">
                    {name}
                </h3>

                {/* Rating */}
                <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1">
                        <Star className="w-3.5 h-3.5 text-amber-400 fill-amber-400" />
                        <span className="text-sm text-white/80">{rating.toFixed(1)}</span>
                    </div>
                    {rating_count > 0 && (
                        <span className="text-xs text-white/40">
                            ({rating_count.toLocaleString()} reviews)
                        </span>
                    )}
                </div>

                {/* Price & Budget Fit */}
                <div className="flex items-center justify-between">
                    <div>
                        <span className="text-lg font-bold text-white">
                            ${price.toFixed(2)}
                        </span>
                    </div>
                    <BudgetFitBadge price={price} budget={budget} />
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-2">
                    {/* Add to Cart Button */}
                    <motion.button
                        onClick={handleAddToCart}
                        disabled={isInCart || isAdding}
                        className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl
                                   font-medium text-sm transition-all ${isInCart
                                ? 'bg-emerald-500/20 text-emerald-400 cursor-default'
                                : 'bg-primary-500 hover:bg-primary-600 text-white'
                            }`}
                        whileHover={!isInCart ? { scale: 1.02 } : {}}
                        whileTap={!isInCart ? { scale: 0.98 } : {}}
                    >
                        {isAdding ? (
                            <motion.div
                                className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                                animate={{ rotate: 360 }}
                                transition={{ duration: 0.6, repeat: Infinity, ease: 'linear' }}
                            />
                        ) : isInCart ? (
                            <>
                                <Check className="w-4 h-4" />
                                In Cart
                            </>
                        ) : (
                            <>
                                <ShoppingCart className="w-4 h-4" />
                                Add to Cart
                            </>
                        )}
                    </motion.button>

                    {/* Info Button */}
                    <motion.button
                        className="p-2.5 bg-white/5 hover:bg-white/10 rounded-xl text-white/60 
                                   hover:text-white/80 transition-colors relative"
                        whileHover={{ scale: 1.05 }}
                        whileTap={{ scale: 0.95 }}
                        onMouseEnter={() => setShowTooltip(true)}
                        onMouseLeave={() => setShowTooltip(false)}
                        onClick={(e) => {
                            e.stopPropagation()
                            onSelect?.(product)
                        }}
                    >
                        <Info className="w-4 h-4" />

                        {/* Tooltip */}
                        {showTooltip && (
                            <motion.div
                                initial={{ opacity: 0, y: 5 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="absolute bottom-full right-0 mb-2 w-48 p-3 bg-dark-100 
                                           border border-white/10 rounded-xl shadow-xl z-10"
                            >
                                <p className="text-xs text-white/60 mb-1">Why recommended:</p>
                                <p className="text-xs text-white/80">
                                    {score >= 0.8
                                        ? '⭐ High relevance to your search'
                                        : score >= 0.6
                                            ? '✓ Good match for your criteria'
                                            : '📊 May interest you based on patterns'
                                    }
                                </p>
                            </motion.div>
                        )}
                    </motion.button>
                </div>
            </div>

            {/* Success Animation Overlay */}
            {isAdded && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 bg-emerald-500/10 flex items-center justify-center"
                >
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="w-16 h-16 bg-emerald-500 rounded-full flex items-center justify-center"
                    >
                        <Check className="w-8 h-8 text-white" />
                    </motion.div>
                </motion.div>
            )}
        </motion.div>
    )
}
