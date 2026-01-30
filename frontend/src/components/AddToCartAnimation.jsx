import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { ShoppingBag, CheckCircle2 } from 'lucide-react'

/**
 * Product fly-to-cart animation
 * Shows the product flying STRAIGHT to the shopping bag icon
 * Provides clear visual feedback that item was added
 */
export default function AddToCartAnimation() {
    const [flyingProducts, setFlyingProducts] = useState([])

    useEffect(() => {
        const handleAddToCart = (event) => {
            const { x, y, productImage, productName, productPrice } = event.detail
            
            // Get cart button position
            const cartButton = document.querySelector('[data-cart-button]')
            const cartRect = cartButton?.getBoundingClientRect()
            
            const startX = x || 500
            const startY = y || 500
            const endX = cartRect ? cartRect.left + cartRect.width / 2 : window.innerWidth - 60
            const endY = cartRect ? cartRect.top + cartRect.height / 2 : 40
            
            const flyingProduct = {
                id: Date.now() + Math.random(),
                startX, startY,
                endX, endY,
                image: productImage,
                name: productName,
                price: productPrice
            }
            
            setFlyingProducts(prev => [...prev, flyingProduct])
            
            setTimeout(() => {
                setFlyingProducts(prev => prev.filter(p => p.id !== flyingProduct.id))
            }, 1400)
        }

        window.addEventListener('add-to-cart-animation', handleAddToCart)
        return () => window.removeEventListener('add-to-cart-animation', handleAddToCart)
    }, [])

    return (
        <>
            {flyingProducts.map(product => (
                <FlyingProductCard key={product.id} product={product} />
            ))}
        </>
    )
}

function FlyingProductCard({ product }) {
    const { startX, startY, endX, endY, image } = product
    const [showBurst, setShowBurst] = useState(false)
    
    useEffect(() => {
        const timer1 = setTimeout(() => setShowBurst(true), 600)
        const timer2 = setTimeout(() => setShowBurst(false), 1200)
        return () => {
            clearTimeout(timer1)
            clearTimeout(timer2)
        }
    }, [])
    
    // Generate trail particles - STRAIGHT path
    const trailParticles = [...Array(8)].map((_, i) => ({
        id: i,
        startX: startX + (Math.random() - 0.5) * 20,
        startY: startY + (Math.random() - 0.5) * 20,
        endX: endX + (Math.random() - 0.5) * 40,
        endY: endY + (Math.random() - 0.5) * 40,
        delay: i * 0.03,
        size: 14 - i,
        color: i % 3 === 0 ? 'from-pink-400 to-rose-500' : 
               i % 3 === 1 ? 'from-violet-400 to-purple-500' : 
               'from-cyan-400 to-blue-500'
    }))

    return (
        <>
            {/* MAIN FLYING ORB - STRAIGHT PATH */}
            <motion.div
                initial={{ 
                    left: startX - 45, 
                    top: startY - 45, 
                    scale: 1, 
                    opacity: 1,
                    rotate: 0
                }}
                animate={{ 
                    left: endX - 20,
                    top: endY - 20,
                    scale: 0.25,
                    opacity: 0,
                    rotate: 360
                }}
                transition={{ 
                    duration: 0.7,
                    ease: [0.4, 0, 0.2, 1],
                }}
                style={{ position: 'fixed', zIndex: 99999, pointerEvents: 'none' }}
            >
                <div className="relative">
                    {/* Outermost glow */}
                    <div className="absolute -inset-8 bg-gradient-to-r from-violet-500/40 via-purple-500/40 to-pink-500/40 rounded-full blur-3xl animate-pulse" />
                    
                    {/* Middle glow ring */}
                    <div className="absolute -inset-4 bg-gradient-to-r from-violet-400/60 to-pink-400/60 rounded-full blur-xl" />
                    
                    {/* Main orb */}
                    <div className="relative w-24 h-24 bg-gradient-to-br from-violet-400 via-purple-500 to-pink-500 rounded-full shadow-2xl flex items-center justify-center border-4 border-white/70 overflow-hidden">
                        {image ? (
                            <img 
                                src={image} 
                                alt="Product"
                                className="w-full h-full object-contain p-2 bg-white/20"
                            />
                        ) : (
                            <ShoppingBag className="w-10 h-10 text-white drop-shadow-lg" />
                        )}
                        <div className="absolute top-2 left-2 w-6 h-6 bg-white/50 rounded-full blur-sm" />
                    </div>
                    
                    {/* Pulse rings */}
                    <motion.div 
                        animate={{ scale: [1, 2, 2.5], opacity: [0.8, 0.3, 0] }}
                        transition={{ duration: 0.4, repeat: 1 }}
                        className="absolute inset-0 border-4 border-white/60 rounded-full"
                    />
                </div>
            </motion.div>
            
            {/* TRAILING SPARKLE PARTICLES */}
            {trailParticles.map(p => (
                <motion.div
                    key={p.id}
                    initial={{ left: p.startX, top: p.startY, scale: 1, opacity: 1 }}
                    animate={{ left: p.endX, top: p.endY, scale: 0, opacity: 0 }}
                    transition={{ duration: 0.6 + p.delay, delay: p.delay, ease: [0.4, 0, 0.2, 1] }}
                    style={{ position: 'fixed', zIndex: 99998, pointerEvents: 'none' }}
                >
                    <div 
                        className={`rounded-full bg-gradient-to-r ${p.color}`}
                        style={{ 
                            width: p.size, 
                            height: p.size,
                            boxShadow: `0 0 ${p.size * 2}px rgba(167, 139, 250, 0.9)`
                        }}
                    />
                </motion.div>
            ))}
            
            {/* BURST AT DESTINATION */}
            {showBurst && (
                <>
                    <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: [0, 3, 4], opacity: [0, 1, 0] }}
                        transition={{ duration: 0.5, ease: 'easeOut' }}
                        style={{ position: 'fixed', left: endX - 60, top: endY - 60, zIndex: 99997, pointerEvents: 'none' }}
                    >
                        <div className="w-30 h-30 rounded-full bg-gradient-to-r from-violet-500/60 via-purple-500/60 to-pink-500/60 blur-2xl" />
                    </motion.div>
                    
                    {[0, 1].map(i => (
                        <motion.div
                            key={i}
                            initial={{ scale: 0, opacity: 0 }}
                            animate={{ scale: [0, 4 + i], opacity: [1, 0] }}
                            transition={{ delay: i * 0.08, duration: 0.4, ease: 'easeOut' }}
                            style={{ position: 'fixed', left: endX - 20, top: endY - 20, zIndex: 99996 - i, pointerEvents: 'none' }}
                        >
                            <div className="w-10 h-10 rounded-full border-2 border-white/80" />
                        </motion.div>
                    ))}
                    
                    <motion.div
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: [0, 1.5, 1], opacity: [0, 1, 0] }}
                        transition={{ delay: 0.15, duration: 0.5 }}
                        style={{ position: 'fixed', left: endX - 16, top: endY - 16, zIndex: 99999, pointerEvents: 'none' }}
                    >
                        <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/50">
                            <CheckCircle2 className="w-5 h-5 text-white" />
                        </div>
                    </motion.div>
                </>
            )}
        </>
    )
}
