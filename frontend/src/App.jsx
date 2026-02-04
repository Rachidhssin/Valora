import { useState, useCallback, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Search, ShoppingBag, Sparkles, TrendingUp, Zap, Grid,
    LayoutGrid, ChevronRight, Package, Star, Filter, X,
    Home, Compass, Heart, Clock, Settings, Menu, ArrowRight,
    Loader2, CheckCircle2, AlertCircle, SlidersHorizontal,
    RefreshCw, ChevronDown, Layers
} from 'lucide-react'
import { useStore } from './store/useStore'
import SearchResultsComponent from './components/SearchResults'
import AddToCartAnimation from './components/AddToCartAnimation'
import CartPage from './components/CartPage'
import AnalyticsDashboard from './components/AnalyticsDashboard'
import { useAnalytics } from './hooks/useAnalytics'

// ============================================================================
// VALORA - Sophisticated E-Commerce Discovery Platform
// ============================================================================

// ============================================================================
// INTERACTION TRACKING - Reinforcement Learning
// ============================================================================

// Track user interactions for RL
const trackInteraction = async (userId, event) => {
    try {
        await fetch(`/api/track/interaction?user_id=${userId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(event)
        })
    } catch (err) {
        console.debug('Tracking failed:', err)
    }
}

// Batch track interactions
const interactionQueue = []
let flushTimeout = null

const queueInteraction = (userId, event) => {
    interactionQueue.push({ ...event, timestamp: new Date().toISOString() })

    // Flush after 5 seconds or 10 events
    if (interactionQueue.length >= 10) {
        flushInteractions(userId)
    } else if (!flushTimeout) {
        flushTimeout = setTimeout(() => flushInteractions(userId), 5000)
    }
}

const flushInteractions = async (userId) => {
    if (interactionQueue.length === 0) return

    const batch = [...interactionQueue]
    interactionQueue.length = 0

    if (flushTimeout) {
        clearTimeout(flushTimeout)
        flushTimeout = null
    }

    try {
        await fetch('/api/track/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: userId,
                interactions: batch
            })
        })
    } catch (err) {
        console.debug('Batch tracking failed:', err)
    }
}

function App() {
    // State
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState([])
    const [searchResponse, setSearchResponse] = useState(null) // Full API response for path-aware rendering
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [activeView, setActiveView] = useState('home') // home, search, cart
    const [showCart, setShowCart] = useState(false)
    const [trendingProducts, setTrendingProducts] = useState([])
    const [recommendedProducts, setRecommendedProducts] = useState([])
    const [discoverProducts, setDiscoverProducts] = useState([])
    const [isOptimizing, setIsOptimizing] = useState(false)
    const [optimizationResult, setOptimizationResult] = useState(null)
    const [showMobileMenu, setShowMobileMenu] = useState(false)
    const [initialLoading, setInitialLoading] = useState(true)

    // Store
    const {
        budget, setBudget, userId, cart, addToCart: storeAddToCart, removeFromCart,
        clearCart, getCartTotal
    } = useStore()

    // Analytics tracking for Success Indicators
    const { trackImpression, trackClick, trackCartAdd, sessionId } = useAnalytics()

    // Wrapped addToCart that tracks for Success Indicators
    const addToCart = useCallback((product, isRecommended = true) => {
        storeAddToCart(product)
        // Track for Success Indicators
        trackCartAdd(product.product_id, product.price, budget, isRecommended)
    }, [storeAddToCart, trackCartAdd, budget])

    // Load initial products on mount
    useEffect(() => {
        loadInitialProducts()
    }, [])

    // Listen for bundle product add to cart events
    useEffect(() => {
        const handleAddBundleProduct = (e) => {
            const product = e.detail
            if (product) {
                addToCart(product)
            }
        }
        window.addEventListener('add-bundle-product-to-cart', handleAddBundleProduct)
        return () => {
            window.removeEventListener('add-bundle-product-to-cart', handleAddBundleProduct)
        }
    }, [addToCart])

    const loadInitialProducts = async () => {
        setInitialLoading(true)
        try {
            // Load multiple product categories in parallel
            const [trendingRes, recommendedRes, discoverRes] = await Promise.all([
                // Trending - Popular electronics
                fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: 'popular electronics bestseller rated',
                        budget: 5000,
                        user_id: userId,
                        cart: [],
                        skip_explanations: true
                    })
                }),
                // Recommended - Gaming setup
                fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: 'gaming keyboard mouse headset setup',
                        budget: 5000,
                        user_id: userId,
                        cart: [],
                        skip_explanations: true
                    })
                }),
                // Discover - Mixed interesting items
                fetch('/api/search', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: '4k monitor webcam streaming setup',
                        budget: 5000,
                        user_id: userId,
                        cart: [],
                        skip_explanations: true
                    })
                })
            ])

            if (trendingRes.ok) {
                const data = await trendingRes.json()
                setTrendingProducts((data.results || []).slice(0, 8))
            }
            if (recommendedRes.ok) {
                const data = await recommendedRes.json()
                setRecommendedProducts((data.results || []).slice(0, 8))
            }
            if (discoverRes.ok) {
                const data = await discoverRes.json()
                setDiscoverProducts((data.results || []).slice(0, 8))
            }
        } catch (err) {
            console.error('Failed to load initial products:', err)
        } finally {
            setInitialLoading(false)
        }
    }

    // Search handler
    const handleSearch = useCallback(async (query) => {
        if (!query?.trim()) return

        setIsLoading(true)
        setError(null)
        setSearchResponse(null) // Clear previous response
        setActiveView('search')

        const startTime = performance.now()

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    budget,
                    user_id: userId,
                    cart,
                    skip_explanations: false // Enable explanations for bundle results
                })
            })

            if (!response.ok) throw new Error('Search failed')

            const data = await response.json()
            const latencyMs = performance.now() - startTime
            console.log('Search response:', data) // Debug log
            setSearchResponse(data) // Store full response for path-aware rendering
            // For backwards compatibility, also set searchResults
            // For deep path, results may be empty but bundle contains the products
            const results = data.results || (data.bundle?.bundle) || []
            setSearchResults(results)

            // Track impressions for Success Indicators
            if (results.length > 0) {
                trackImpression(results, budget, query, data.path || 'smart', latencyMs, userId)
            }
        } catch (err) {
            setError('Failed to search. Please try again.')
            console.error(err)
        } finally {
            setIsLoading(false)
        }
    }, [budget, userId, cart, trackImpression])

    // Optimize bundle handler
    const handleOptimize = async () => {
        if (cart.length === 0) return

        setIsOptimizing(true)
        setOptimizationResult(null)

        try {
            const response = await fetch('/api/optimize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    cart,
                    budget,
                    user_id: userId
                })
            })

            if (response.ok) {
                const data = await response.json()
                if (data.success) {
                    setOptimizationResult(data)
                }
            }
        } catch (err) {
            console.error('Optimization failed:', err)
        } finally {
            setIsOptimizing(false)
        }
    }

    const cartTotal = getCartTotal()
    const cartCount = cart.length

    // Quick search categories
    const categories = [
        { id: 'monitors', label: 'Monitors', icon: '🖥️', query: '4k gaming monitor', color: 'from-blue-500/20 to-cyan-500/20' },
        { id: 'laptops', label: 'Laptops', icon: '💻', query: 'gaming laptop rtx', color: 'from-purple-500/20 to-pink-500/20' },
        { id: 'keyboards', label: 'Keyboards', icon: '⌨️', query: 'mechanical keyboard rgb', color: 'from-amber-500/20 to-orange-500/20' },
        { id: 'mice', label: 'Mice', icon: '🖱️', query: 'gaming mouse wireless', color: 'from-green-500/20 to-emerald-500/20' },
        { id: 'headsets', label: 'Audio', icon: '🎧', query: 'gaming headset microphone', color: 'from-red-500/20 to-rose-500/20' },
        { id: 'webcams', label: 'Webcams', icon: '📷', query: 'webcam 1080p streaming', color: 'from-violet-500/20 to-indigo-500/20' },
    ]

    return (
        <div className="min-h-screen bg-[#08080c] text-white">
            {/* Background Effects */}
            <div className="fixed inset-0 pointer-events-none">
                <div className="absolute top-0 left-1/4 w-96 h-96 bg-violet-600/10 rounded-full blur-[128px]" />
                <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-cyan-600/10 rounded-full blur-[128px]" />
            </div>

            {/* ==================== HEADER ==================== */}
            <header className="fixed top-0 left-0 right-0 z-50 bg-[#08080c]/90 backdrop-blur-2xl border-b border-white/[0.05]">
                <div className="max-w-[1600px] mx-auto px-4 lg:px-8">
                    <div className="flex items-center justify-between h-16 lg:h-20">
                        {/* Logo */}
                        <motion.div
                            className="flex items-center gap-3 cursor-pointer"
                            onClick={() => setActiveView('home')}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            <div className="relative">
                                <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-violet-500 via-purple-500 to-cyan-500 
                                              flex items-center justify-center shadow-lg shadow-violet-500/30">
                                    <Sparkles className="w-5 h-5 text-white" />
                                </div>
                                <div className="absolute -inset-1 bg-gradient-to-br from-violet-500 to-cyan-500 rounded-2xl blur opacity-30" />
                            </div>
                            <div className="hidden sm:block">
                                <h1 className="text-xl font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                                    Valora
                                </h1>
                                <p className="text-[10px] text-white/40 -mt-0.5 tracking-wide">SMART DISCOVERY</p>
                            </div>
                        </motion.div>

                        {/* Search Bar - Desktop */}
                        <div className="hidden md:flex flex-1 max-w-2xl mx-8">
                            <SearchBar
                                value={searchQuery}
                                onChange={setSearchQuery}
                                onSearch={() => handleSearch(searchQuery)}
                                isLoading={isLoading}
                            />
                        </div>

                        {/* Right Actions */}
                        <div className="flex items-center gap-3">
                            {/* Dashboard Button (Admin) */}
                            <button
                                onClick={() => setActiveView('dashboard')}
                                className="hidden md:flex p-2.5 text-white/40 hover:text-white bg-white/[0.03] 
                                         hover:bg-white/[0.06] rounded-xl border border-white/[0.06] transition-all"
                                title="Analytics Dashboard"
                            >
                                <TrendingUp className="w-4 h-4" />
                            </button>

                            {/* Budget Selector */}
                            <div className="hidden lg:flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] 
                                          rounded-xl border border-white/[0.06] hover:border-white/10 transition-colors">
                                <SlidersHorizontal className="w-4 h-4 text-white/40" />
                                <span className="text-xs text-white/40">Budget</span>
                                <div className="flex items-center gap-1">
                                    <span className="text-white/60">$</span>
                                    <input
                                        type="number"
                                        value={budget}
                                        onChange={(e) => setBudget(Number(e.target.value))}
                                        className="w-16 bg-transparent text-white font-medium text-sm focus:outline-none"
                                    />
                                </div>
                            </div>

                            {/* Cart Button */}
                            <motion.button
                                data-cart-button
                                onClick={() => setShowCart(true)}
                                whileHover={{ scale: 1.05 }}
                                whileTap={{ scale: 0.95 }}
                                className="relative p-3 bg-white/[0.03] hover:bg-white/[0.06] rounded-xl 
                                         border border-white/[0.06] hover:border-violet-500/30 transition-all group"
                            >
                                <ShoppingBag className="w-5 h-5 text-white/60 group-hover:text-white transition-colors" />
                                {cartCount > 0 && (
                                    <motion.span
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-gradient-to-r from-violet-500 to-purple-500
                                                 rounded-full text-[10px] flex items-center justify-center font-bold shadow-lg shadow-violet-500/30"
                                    >
                                        {cartCount}
                                    </motion.span>
                                )}
                            </motion.button>

                            {/* Mobile Menu */}
                            <button
                                onClick={() => setShowMobileMenu(!showMobileMenu)}
                                className="md:hidden p-3 bg-white/[0.03] rounded-xl border border-white/[0.06]"
                            >
                                <Menu className="w-5 h-5" />
                            </button>
                        </div>
                    </div>

                    {/* Search Bar - Mobile */}
                    <div className="md:hidden pb-4">
                        <SearchBar
                            value={searchQuery}
                            onChange={setSearchQuery}
                            onSearch={() => handleSearch(searchQuery)}
                            isLoading={isLoading}
                        />
                    </div>
                </div>
            </header>

            {/* ==================== MAIN CONTENT ==================== */}
            <main className="pt-24 md:pt-28 pb-20 min-h-screen relative">
                <div className="max-w-[1600px] mx-auto px-4 lg:px-8">

                    {/* Error Display */}
                    <AnimatePresence>
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-2xl 
                                         flex items-center gap-3 backdrop-blur-sm"
                            >
                                <AlertCircle className="w-5 h-5 text-red-400" />
                                <span className="text-red-300 text-sm">{error}</span>
                                <button onClick={() => setError(null)} className="ml-auto p-1 hover:bg-white/10 rounded-lg">
                                    <X className="w-4 h-4 text-white/50 hover:text-white" />
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* HOME VIEW */}
                    {activeView === 'home' && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="space-y-16"
                        >
                            {/* Hero Section */}
                            <section className="text-center py-12 lg:py-20">
                                <motion.div
                                    initial={{ opacity: 0, y: 30 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.6 }}
                                >
                                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-violet-500/10 
                                                  border border-violet-500/20 rounded-full mb-6">
                                        <Zap className="w-4 h-4 text-violet-400" />
                                        <span className="text-sm text-violet-300">AI-Powered Discovery</span>
                                    </div>

                                    <h2 className="text-4xl md:text-6xl lg:text-7xl font-bold mb-6 leading-tight">
                                        Find your perfect
                                        <br />
                                        <span className="bg-gradient-to-r from-violet-400 via-purple-400 to-cyan-400 
                                                       bg-clip-text text-transparent">
                                            tech setup
                                        </span>
                                    </h2>

                                    <p className="text-lg text-white/50 max-w-xl mx-auto leading-relaxed">
                                        Smart product discovery with bundle optimization.
                                        Find the best products that fit your budget perfectly.
                                    </p>
                                </motion.div>
                            </section>

                            {/* Quick Categories */}
                            <section>
                                <SectionHeader
                                    icon={<Compass className="w-5 h-5" />}
                                    title="Explore Categories"
                                    iconColor="text-violet-400"
                                />
                                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
                                    {categories.map((cat, i) => (
                                        <motion.button
                                            key={cat.id}
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: i * 0.05 }}
                                            whileHover={{ y: -4, scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            onClick={() => {
                                                setSearchQuery(cat.query)
                                                handleSearch(cat.query)
                                            }}
                                            className={`relative p-6 bg-gradient-to-br ${cat.color} 
                                                      border border-white/[0.06] hover:border-white/20 
                                                      rounded-2xl transition-all group overflow-hidden`}
                                        >
                                            <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                            <div className="relative">
                                                <div className="text-3xl mb-3">{cat.icon}</div>
                                                <p className="text-sm font-medium text-white/80 group-hover:text-white transition-colors">
                                                    {cat.label}
                                                </p>
                                            </div>
                                        </motion.button>
                                    ))}
                                </div>
                            </section>

                            {/* Loading Skeleton */}
                            {initialLoading && (
                                <div className="space-y-16">
                                    <ProductGridSkeleton />
                                    <ProductGridSkeleton />
                                </div>
                            )}

                            {/* Trending Products */}
                            {!initialLoading && trendingProducts.length > 0 && (
                                <section>
                                    <SectionHeader
                                        icon={<TrendingUp className="w-5 h-5" />}
                                        title="Trending Now"
                                        subtitle="Most popular products this week"
                                        iconColor="text-cyan-400"
                                        action={
                                            <button className="text-sm text-violet-400 hover:text-violet-300 
                                                             flex items-center gap-1 transition-colors">
                                                View all <ChevronRight className="w-4 h-4" />
                                            </button>
                                        }
                                    />
                                    <ProductGrid products={trendingProducts} onAddToCart={addToCart} cart={cart} userId={userId} onTrackClick={trackClick} budget={budget} />
                                </section>
                            )}

                            {/* Recommended */}
                            {!initialLoading && recommendedProducts.length > 0 && (
                                <section>
                                    <SectionHeader
                                        icon={<Heart className="w-5 h-5" />}
                                        title="Recommended for You"
                                        subtitle="Based on popular choices"
                                        iconColor="text-rose-400"
                                        action={
                                            <button className="text-sm text-violet-400 hover:text-violet-300 
                                                             flex items-center gap-1 transition-colors">
                                                View all <ChevronRight className="w-4 h-4" />
                                            </button>
                                        }
                                    />
                                    <ProductGrid products={recommendedProducts} onAddToCart={addToCart} cart={cart} userId={userId} onTrackClick={trackClick} budget={budget} />
                                </section>
                            )}

                            {/* Discover */}
                            {!initialLoading && discoverProducts.length > 0 && (
                                <section>
                                    <SectionHeader
                                        icon={<Sparkles className="w-5 h-5" />}
                                        title="Discover"
                                        subtitle="Explore new products"
                                        iconColor="text-amber-400"
                                        action={
                                            <button className="text-sm text-violet-400 hover:text-violet-300 
                                                             flex items-center gap-1 transition-colors">
                                                View all <ChevronRight className="w-4 h-4" />
                                            </button>
                                        }
                                    />
                                    <ProductGrid products={discoverProducts} onAddToCart={addToCart} cart={cart} userId={userId} onTrackClick={trackClick} budget={budget} />
                                </section>
                            )}
                        </motion.div>
                    )}

                    {/* SEARCH RESULTS VIEW */}
                    {activeView === 'search' && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="space-y-8"
                        >
                            {/* Search Header */}
                            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <motion.button
                                        onClick={() => setActiveView('home')}
                                        whileHover={{ x: -4 }}
                                        className="text-sm text-white/50 hover:text-white mb-3 
                                                 flex items-center gap-1 transition-colors"
                                    >
                                        <ArrowRight className="w-4 h-4 rotate-180" />
                                        Back to Home
                                    </motion.button>
                                    <h2 className="text-2xl md:text-3xl font-bold">
                                        Results for "<span className="text-violet-400">{searchQuery}</span>"
                                    </h2>
                                    <p className="text-white/50 text-sm mt-2">
                                        {searchResponse?.path === 'deep'
                                            ? `${searchResponse?.bundle?.bundle?.length || 0} items in optimized bundle`
                                            : `${searchResults.length} products found`
                                        }
                                        {searchResponse?.path && (
                                            <span className="ml-2 text-violet-400">
                                                • {searchResponse.path.toUpperCase()} path
                                            </span>
                                        )}
                                    </p>
                                </div>

                                {/* Filters (placeholder) */}
                                <div className="flex items-center gap-3">
                                    <button className="flex items-center gap-2 px-4 py-2.5 bg-white/[0.03] 
                                                     border border-white/[0.06] hover:border-white/10 
                                                     rounded-xl text-sm text-white/60 hover:text-white transition-all">
                                        <Filter className="w-4 h-4" />
                                        Filters
                                    </button>
                                </div>
                            </div>

                            {/* Loading */}
                            {isLoading && (
                                <div className="py-20 text-center">
                                    <div className="relative inline-block">
                                        <Loader2 className="w-12 h-12 text-violet-400 animate-spin" />
                                        <div className="absolute inset-0 bg-violet-500/20 rounded-full blur-xl" />
                                    </div>
                                    <p className="mt-6 text-white/50">Searching products...</p>
                                </div>
                            )}

                            {/* Path-aware Results using SearchResults component */}
                            {!isLoading && searchResponse && searchResponse.path && (
                                <SearchResultsComponent
                                    result={searchResponse}
                                    onTrackClick={trackClick}
                                    onAddToCart={addToCart}
                                    budget={budget}
                                />
                            )}

                            {/* Fallback: Simple Results Grid (when no path info) */}
                            {!isLoading && (!searchResponse || !searchResponse.path) && searchResults.length > 0 && (
                                <ProductGrid
                                    products={searchResults}
                                    onAddToCart={addToCart}
                                    cart={cart}
                                    columns={4}
                                    userId={userId}
                                    onTrackClick={trackClick}
                                    budget={budget}
                                />
                            )}

                            {/* No Results */}
                            {!isLoading && (!searchResponse || (!searchResponse.results?.length && !searchResponse.bundle?.bundle?.length)) && searchResults.length === 0 && (
                                <div className="py-20 text-center">
                                    <div className="relative inline-block mb-6">
                                        <Package className="w-20 h-20 text-white/10" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-white/80">No products found</h3>
                                    <p className="text-white/50 mt-2 mb-6">Try a different search term</p>
                                    <button
                                        onClick={() => setActiveView('home')}
                                        className="px-6 py-3 bg-violet-500 hover:bg-violet-600 rounded-xl 
                                                 font-medium transition-colors"
                                    >
                                        Explore Products
                                    </button>
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* DASHBOARD VIEW */}
                    {activeView === 'dashboard' && (
                        <AnalyticsDashboard onClose={() => setActiveView('home')} />
                    )}
                </div>
            </main>

            {/* ==================== FULL PAGE CART ==================== */}
            <AnimatePresence>
                {showCart && (
                    <CartPage
                        isOpen={showCart}
                        onClose={() => setShowCart(false)}
                        cart={cart}
                        cartTotal={cartTotal}
                        budget={budget}
                        userId={userId}
                        onRemove={removeFromCart}
                        onClear={clearCart}
                        onOptimize={handleOptimize}
                        isOptimizing={isOptimizing}
                        optimizationResult={optimizationResult}
                        setOptimizationResult={setOptimizationResult}
                        onAddToCartFromOptimize={(item) => addToCart({
                            product_id: item.product_id,
                            name: item.name,
                            price: item.price,
                            category: item.category,
                            brand: item.brand,
                            image_url: item.image_url,
                            rating: item.rating
                        })}
                        addToCart={addToCart}
                    />
                )}
            </AnimatePresence>

            {/* Footer */}
            <footer className="border-t border-white/[0.05] py-8 mt-20">
                <div className="max-w-[1600px] mx-auto px-4 lg:px-8 text-center">
                    <p className="text-sm text-white/30">
                        Built with <span className="text-violet-400">Qdrant</span>, <span className="text-cyan-400">Groq</span>, and <span className="text-purple-400">OR-Tools</span>
                    </p>
                    <p className="text-xs text-white/20 mt-2">Valora v3 • Smart Commerce Discovery Engine</p>
                </div>
            </footer>

            {/* Add to Cart Flying Animation */}
            <AddToCartAnimation />
        </div>
    )
}

// ============================================================================
// COMPONENTS
// ============================================================================

// Section Header Component
function SectionHeader({ icon, title, subtitle, iconColor, action }) {
    return (
        <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
                <div className={`p-2 bg-white/[0.03] rounded-xl ${iconColor}`}>
                    {icon}
                </div>
                <div>
                    <h3 className="text-lg font-semibold">{title}</h3>
                    {subtitle && <p className="text-sm text-white/40">{subtitle}</p>}
                </div>
            </div>
            {action}
        </div>
    )
}

// Search Bar Component
function SearchBar({ value, onChange, onSearch, isLoading }) {
    return (
        <div className="relative w-full group">
            <div className="absolute -inset-0.5 bg-gradient-to-r from-violet-500/50 to-cyan-500/50 
                          rounded-2xl opacity-0 group-focus-within:opacity-100 blur transition-opacity" />
            <div className="relative flex items-center bg-white/[0.03] border border-white/[0.06] 
                          group-focus-within:border-transparent rounded-2xl overflow-hidden">
                <Search className="absolute left-4 w-5 h-5 text-white/30" />
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && onSearch()}
                    placeholder="Search products, brands, categories..."
                    className="w-full pl-12 pr-28 py-4 bg-transparent text-white placeholder-white/30
                             focus:outline-none text-sm"
                />
                <button
                    onClick={onSearch}
                    disabled={isLoading}
                    className="absolute right-2 px-5 py-2.5 bg-gradient-to-r from-violet-500 to-purple-500 
                             hover:from-violet-600 hover:to-purple-600 rounded-xl font-medium text-sm
                             transition-all disabled:opacity-50 shadow-lg shadow-violet-500/25"
                >
                    {isLoading ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                        'Search'
                    )}
                </button>
            </div>
        </div>
    )
}

// Product Grid Component
function ProductGrid({ products, onAddToCart, cart, columns = 4, userId, onTrackClick, budget }) {
    if (!products || products.length === 0) return null

    const gridCols = {
        2: 'lg:grid-cols-2',
        3: 'lg:grid-cols-3',
        4: 'lg:grid-cols-4',
    }

    // Track add to cart with RL
    const handleAddToCart = (product) => {
        onAddToCart(product)
        if (userId) {
            trackInteraction(userId, {
                event_type: 'add_to_cart',
                product_id: product.product_id,
                product_name: product.name,
                product_category: product.category,
                product_price: product.price,
                source: 'product_grid'
            })
        }
    }

    // Track click for Success Indicators
    const handleProductClick = (product, index) => {
        if (onTrackClick) {
            onTrackClick(product.product_id, index, product.price, budget)
        }
    }

    return (
        <div className={`grid grid-cols-2 md:grid-cols-3 ${gridCols[columns] || 'lg:grid-cols-4'} gap-4 md:gap-6`}>
            {products.map((product, index) => (
                <ProductCard
                    key={product.product_id || index}
                    product={product}
                    onAddToCart={handleAddToCart}
                    isInCart={cart.some(item => item.product_id === product.product_id)}
                    index={index}
                    userId={userId}
                    onProductClick={(p) => handleProductClick(p, index)}
                />
            ))}
        </div>
    )
}

// Product Grid Skeleton
function ProductGridSkeleton() {
    return (
        <div className="space-y-6">
            <div className="flex items-center gap-3">
                <div className="w-9 h-9 bg-white/[0.03] rounded-xl animate-pulse" />
                <div className="h-6 w-40 bg-white/[0.03] rounded-lg animate-pulse" />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 md:gap-6">
                {[...Array(8)].map((_, i) => (
                    <div key={i} className="bg-white/[0.02] rounded-2xl overflow-hidden animate-pulse">
                        <div className="aspect-square bg-white/[0.03]" />
                        <div className="p-4 space-y-3">
                            <div className="h-3 w-16 bg-white/[0.05] rounded" />
                            <div className="h-4 w-full bg-white/[0.05] rounded" />
                            <div className="h-4 w-3/4 bg-white/[0.05] rounded" />
                            <div className="h-6 w-20 bg-white/[0.05] rounded" />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    )
}

// Product Card Component
function ProductCard({ product, onAddToCart, isInCart, index, userId, onProductClick }) {
    const {
        product_id,
        name = 'Unknown Product',
        price = 0,
        rating = 0,
        category = '',
        brand = '',
        image_url = '',
        score = 0,
        description = ''
    } = product

    // Dwell time tracking
    const dwellStart = useRef(null)

    const handleMouseEnter = () => {
        dwellStart.current = Date.now()
        // Track view event
        if (userId) {
            queueInteraction(userId, {
                event_type: 'view',
                product_id,
                product_name: name,
                product_category: category,
                product_price: price,
                position: index
            })
        }
    }

    const handleMouseLeave = () => {
        if (dwellStart.current && userId) {
            const dwellTime = Date.now() - dwellStart.current
            if (dwellTime > 1000) { // Only track if > 1 second
                queueInteraction(userId, {
                    event_type: 'dwell',
                    product_id,
                    product_category: category,
                    product_price: price,
                    dwell_time_ms: dwellTime
                })
            }
        }
        dwellStart.current = null
    }

    const handleClick = () => {
        if (userId) {
            trackInteraction(userId, {
                event_type: 'click',
                product_id,
                product_name: name,
                product_category: category,
                product_price: price,
                position: index,
                source: 'product_card'
            })
        }
        if (onProductClick) onProductClick(product)
    }

    // Extract key features from name/description
    const features = []
    const text = (name + ' ' + description).toLowerCase()
    if (text.includes('wireless')) features.push('Wireless')
    if (text.includes('rgb')) features.push('RGB')
    if (text.includes('4k')) features.push('4K')
    if (text.includes('gaming')) features.push('Gaming')
    if (text.includes('mechanical')) features.push('Mechanical')
    if (text.includes('bluetooth')) features.push('Bluetooth')
    if (text.includes('usb-c') || text.includes('usb c')) features.push('USB-C')
    if (text.includes('noise cancel')) features.push('ANC')

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03, duration: 0.4 }}
            whileHover={{ y: -4 }}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            onClick={handleClick}
            className="group relative bg-white/[0.02] hover:bg-white/[0.04] 
                     border border-white/[0.06] hover:border-violet-500/30 
                     rounded-2xl overflow-hidden transition-all duration-300 flex flex-col cursor-pointer"
        >
            {/* Hover Glow */}
            <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
                <div className="absolute inset-0 bg-gradient-to-br from-violet-500/5 to-cyan-500/5" />
            </div>

            {/* Image */}
            <div className="relative aspect-square bg-gradient-to-br from-white/[0.02] to-transparent p-4 overflow-hidden">
                {image_url ? (
                    <motion.img
                        src={image_url}
                        alt={name}
                        className="w-full h-full object-contain"
                        loading="lazy"
                        whileHover={{ scale: 1.05 }}
                        transition={{ duration: 0.3 }}
                    />
                ) : (
                    <div className="w-full h-full flex items-center justify-center text-4xl text-white/10">
                        📦
                    </div>
                )}

                {/* Match Score Badge */}
                {score > 0 && (
                    <div className="absolute top-3 left-3 px-2.5 py-1 bg-gradient-to-r from-violet-500 to-purple-500 
                                  backdrop-blur-sm rounded-lg text-xs font-semibold shadow-lg flex items-center gap-1">
                        <Zap className="w-3 h-3" />
                        {Math.round(score * 100)}% Match
                    </div>
                )}

                {/* Category Badge */}
                {category && (
                    <div className="absolute top-3 right-3 px-2 py-1 bg-black/50 backdrop-blur-sm 
                                  rounded-lg text-[10px] text-white/60 uppercase tracking-wider">
                        {category.split(',')[0]}
                    </div>
                )}
            </div>

            {/* Content */}
            <div className="relative p-4 flex-1 flex flex-col">
                {/* Brand */}
                {brand && brand !== 'Unknown' && (
                    <p className="text-xs text-violet-400 font-medium uppercase tracking-wider mb-1">
                        {brand}
                    </p>
                )}

                {/* Name */}
                <h3 className="text-sm font-medium text-white/90 line-clamp-2 leading-snug mb-2">
                    {name}
                </h3>

                {/* Features Tags */}
                {features.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                        {features.slice(0, 3).map((feat, i) => (
                            <span key={i} className="px-2 py-0.5 bg-white/[0.05] border border-white/[0.08] 
                                                    rounded-md text-[10px] text-white/50">
                                {feat}
                            </span>
                        ))}
                    </div>
                )}

                {/* Spacer */}
                <div className="flex-1" />

                {/* Rating & Price Row */}
                <div className="flex items-center justify-between mt-2">
                    {/* Rating */}
                    {rating > 0 ? (
                        <div className="flex items-center gap-1">
                            <div className="flex items-center">
                                {[...Array(5)].map((_, i) => (
                                    <Star
                                        key={i}
                                        className={`w-3 h-3 ${i < Math.round(rating)
                                            ? 'text-amber-400 fill-amber-400'
                                            : 'text-white/20'}`}
                                    />
                                ))}
                            </div>
                            <span className="text-xs text-white/40 ml-1">{rating.toFixed(1)}</span>
                        </div>
                    ) : (
                        <div />
                    )}

                    {/* Price */}
                    <div className="text-right">
                        <span className="text-lg font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                            ${price.toFixed(2)}
                        </span>
                    </div>
                </div>

                {/* Add to Cart Button - Always Visible */}
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={(e) => {
                        e.stopPropagation()
                        if (!isInCart) {
                            // Dispatch animation event
                            const rect = e.currentTarget.getBoundingClientRect()
                            window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
                                detail: {
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    productImage: image_url,
                                    productName: name,
                                    productPrice: price
                                }
                            }))
                            onAddToCart({ product_id, name, price, category, brand, image_url, rating })
                        }
                    }}
                    disabled={isInCart}
                    className={`mt-4 w-full py-2.5 rounded-xl font-medium text-sm
                              flex items-center justify-center gap-2 transition-all
                              ${isInCart
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-gradient-to-r from-violet-500 to-purple-500 hover:from-violet-600 hover:to-purple-600 text-white shadow-lg shadow-violet-500/20'
                        }`}
                >
                    {isInCart ? (
                        <>
                            <CheckCircle2 className="w-4 h-4" />
                            Added to Cart
                        </>
                    ) : (
                        <>
                            <ShoppingBag className="w-4 h-4" />
                            Add to Cart
                        </>
                    )}
                </motion.button>
            </div>
        </motion.div>
    )
}

// Bundle Product Card with Alternatives - For Optimization Results
function BundleProductCard({ item, index, alternatives, userId, onSwap }) {
    const [showAlts, setShowAlts] = useState(false)

    // Swap handler
    const handleSwap = async (altProduct) => {
        // Track the swap for RL
        try {
            await fetch('http://localhost:8123/api/bundle/swap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    slot_id: item.slot_id,
                    old_product_id: item.product_id,
                    new_product_id: altProduct.product_id,
                    old_price: item.price,
                    new_price: altProduct.price
                })
            })
        } catch (err) {
            console.log('Swap tracking failed:', err)
        }

        onSwap(index, altProduct)
        setShowAlts(false)
    }

    return (
        <motion.div
            initial={{ opacity: 0, x: -30, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            transition={{ delay: 0.6 + index * 0.1, type: 'spring', damping: 20 }}
            className="relative"
        >
            {/* Main Product Card */}
            <div
                onClick={() => {
                    // If suggestion (not from cart), show info card
                    if (item.is_suggestion) {
                        window.dispatchEvent(new CustomEvent('bundle-select-product', { detail: item }))
                    }
                    // Toggle alternatives if available
                    if (alternatives.length > 0) {
                        setShowAlts(!showAlts)
                    }
                }}
                className={`relative bg-gradient-to-br from-white/[0.04] to-white/[0.01] 
                     border ${showAlts ? 'border-cyan-500/50' : 'border-white/[0.08] hover:border-violet-500/40'} 
                     rounded-2xl overflow-hidden transition-all group cursor-pointer`}
            >
                {/* Number Badge */}
                <div className="absolute top-4 left-4 w-8 h-8 bg-gradient-to-br from-violet-500 to-purple-600 
                              rounded-xl flex items-center justify-center text-sm font-bold shadow-lg shadow-violet-500/30 z-10">
                    {index + 1}
                </div>

                {/* From Cart Badge */}
                {!item.is_suggestion && (
                    <div className="absolute top-4 right-4 px-2 py-1 bg-emerald-500/20 border border-emerald-500/30 
                                  rounded-lg text-[10px] text-emerald-400 uppercase tracking-wide z-10">
                        From Cart
                    </div>
                )}

                {/* Alternatives indicator */}
                {alternatives.length > 0 && item.is_suggestion && (
                    <div className="absolute top-4 right-4 px-2 py-1 bg-cyan-500/20 border border-cyan-500/30 
                                  rounded-lg text-[10px] text-cyan-400 flex items-center gap-1 z-10">
                        <RefreshCw className="w-3 h-3" />
                        {alternatives.length} options
                    </div>
                )}

                <div className="flex gap-4 p-4">
                    {/* Large Product Image */}
                    <div className="w-28 h-28 bg-gradient-to-br from-white/[0.05] to-transparent 
                                  rounded-xl overflow-hidden flex-shrink-0 relative group-hover:scale-105 transition-transform">
                        {item.image_url ? (
                            <img
                                src={item.image_url}
                                alt={item.name}
                                className="w-full h-full object-contain p-2"
                            />
                        ) : (
                            <div className="w-full h-full flex items-center justify-center text-3xl">📦</div>
                        )}
                    </div>

                    {/* Product Details */}
                    <div className="flex-1 min-w-0 py-1">
                        {/* Brand */}
                        {item.brand && item.brand !== 'Unknown' && (
                            <p className="text-xs text-violet-400 font-semibold uppercase tracking-wider mb-1">
                                {item.brand}
                            </p>
                        )}

                        {/* Name */}
                        <h4 className="text-base font-semibold text-white/95 leading-snug mb-2 line-clamp-2">
                            {item.name}
                        </h4>

                        {/* Category & Rating Row */}
                        <div className="flex items-center gap-3 mb-3">
                            {item.category && (
                                <span className="px-2 py-1 bg-white/[0.05] border border-white/[0.08] 
                                               rounded-lg text-[10px] text-white/50 uppercase tracking-wide">
                                    {item.category.split(',')[0]}
                                </span>
                            )}
                            {item.rating > 0 && (
                                <div className="flex items-center gap-1.5">
                                    <div className="flex">
                                        {[...Array(5)].map((_, idx) => (
                                            <Star
                                                key={idx}
                                                className={`w-3.5 h-3.5 ${idx < Math.round(item.rating)
                                                    ? 'text-amber-400 fill-amber-400'
                                                    : 'text-white/10'}`}
                                            />
                                        ))}
                                    </div>
                                    <span className="text-xs text-white/50">{item.rating?.toFixed(1)}</span>
                                </div>
                            )}
                        </div>

                        {/* Features */}
                        {(() => {
                            const features = []
                            const text = (item.name || '').toLowerCase()
                            if (text.includes('wireless')) features.push('Wireless')
                            if (text.includes('rgb')) features.push('RGB')
                            if (text.includes('4k')) features.push('4K')
                            if (text.includes('gaming')) features.push('Gaming')
                            if (text.includes('mechanical')) features.push('Mechanical')
                            if (text.includes('bluetooth')) features.push('Bluetooth')
                            return features.length > 0 ? (
                                <div className="flex flex-wrap gap-1.5">
                                    {features.slice(0, 4).map((feat, idx) => (
                                        <span key={idx} className="px-2 py-0.5 bg-cyan-500/10 border border-cyan-500/20 
                                                                 rounded-md text-[10px] text-cyan-400">
                                            {feat}
                                        </span>
                                    ))}
                                </div>
                            ) : null
                        })()}
                    </div>

                    {/* Price Section */}
                    <div className="flex flex-col items-end justify-between py-1">
                        <div className="text-right">
                            <p className="text-2xl font-bold bg-gradient-to-r from-white to-white/80 bg-clip-text text-transparent">
                                ${item.price?.toFixed(2)}
                            </p>
                        </div>
                        <div className="flex items-center gap-1 text-emerald-400">
                            <CheckCircle2 className="w-4 h-4" />
                            <span className="text-xs font-medium">Included</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Alternatives Dropdown */}
            <AnimatePresence>
                {showAlts && alternatives.length > 0 && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="mt-2 ml-8 space-y-2 overflow-hidden"
                    >
                        <p className="text-[10px] text-cyan-400/70 uppercase tracking-wider flex items-center gap-2">
                            <ArrowRight className="w-3 h-3" />
                            Swap with alternative
                        </p>
                        {alternatives.map((alt, altIdx) => (
                            <motion.div
                                key={alt.product_id || altIdx}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: altIdx * 0.05 }}
                                className="flex items-center gap-3 p-3 bg-white/[0.02] border border-white/[0.06] 
                                         hover:border-cyan-500/40 rounded-xl cursor-pointer group/alt transition-all"
                                onClick={(e) => {
                                    e.stopPropagation()
                                    handleSwap(alt)
                                }}
                            >
                                {/* Alt Image */}
                                <div className="w-14 h-14 bg-white/[0.03] rounded-lg overflow-hidden flex-shrink-0">
                                    {alt.image_url ? (
                                        <img src={alt.image_url} alt={alt.name} className="w-full h-full object-contain p-1" />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center text-xl">📦</div>
                                    )}
                                </div>

                                {/* Alt Details */}
                                <div className="flex-1 min-w-0">
                                    <h5 className="text-sm font-medium text-white/80 line-clamp-1">{alt.name}</h5>
                                    <div className="flex items-center gap-2 mt-1">
                                        {alt.rating > 0 && (
                                            <div className="flex items-center gap-1">
                                                <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                                                <span className="text-[10px] text-white/50">{alt.rating?.toFixed(1)}</span>
                                            </div>
                                        )}
                                        {alt.brand && (
                                            <span className="text-[10px] text-white/40">{alt.brand}</span>
                                        )}
                                    </div>
                                </div>

                                {/* Alt Price & Swap Button */}
                                <div className="flex items-center gap-3">
                                    <div className="text-right">
                                        <p className="text-lg font-bold text-white/90">${alt.price?.toFixed(2)}</p>
                                        {alt.price !== item.price && (
                                            <p className={`text-[10px] ${alt.price < item.price ? 'text-emerald-400' : 'text-amber-400'}`}>
                                                {alt.price < item.price ? '▼' : '▲'} ${Math.abs(alt.price - item.price).toFixed(2)}
                                            </p>
                                        )}
                                    </div>
                                    <div className="p-2 bg-cyan-500/20 group-hover/alt:bg-cyan-500 
                                                  rounded-lg transition-all">
                                        <RefreshCw className="w-4 h-4 text-cyan-400 group-hover/alt:text-white" />
                                    </div>
                                </div>
                            </motion.div>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    )
}

export default App

