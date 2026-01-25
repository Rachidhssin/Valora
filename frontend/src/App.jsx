import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { RotateCcw, Moon, Sun, Sparkles } from 'lucide-react'

// Components
import Header from './components/Header'
import MultimodalSearchBar from './components/MultimodalSearchBar'
import ProductCard from './components/ProductCard'
import FinancialDNACard from './components/FinancialDNACard'
import BundleCart from './components/BundleCart'
import CounterfactualSlider from './components/CounterfactualSlider'

// Store
import { useStore } from './store/useStore'

function App() {
    const [searchResult, setSearchResult] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)
    const [darkMode, setDarkMode] = useState(true)
    const [showCounterfactual, setShowCounterfactual] = useState(false)

    const {
        budget,
        setBudget,
        userId,
        cart,
        resetToDemo,
        setLastMetrics,
        bundleQualityScore
    } = useStore()

    // Handle multimodal search
    const handleSearch = useCallback(async (searchData) => {
        const { text, image, budget: searchBudget, context } = searchData

        if (!text?.trim() && !image) return

        setIsLoading(true)
        setError(null)

        try {
            console.log('🔍 Searching for:', text, 'Budget:', searchBudget || budget)

            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: text || '',
                    budget: searchBudget || budget,
                    user_id: userId,
                    cart,
                    skip_explanations: true // Skip slow LLM for faster response
                })
            })

            if (!response.ok) {
                const errorText = await response.text()
                console.error('API Error:', response.status, errorText)
                throw new Error(`Search failed: ${response.status}`)
            }

            const data = await response.json()
            console.log('📦 Search result:', data)

            // Extract results from different response formats
            let results = []
            if (data.results && Array.isArray(data.results)) {
                results = data.results
            } else if (data.bundle?.items) {
                results = data.bundle.items
            } else if (data.bundle?.bundle) {
                // Deep path returns bundle.bundle with items
                results = data.bundle.bundle || []
            }

            console.log('📊 Extracted products:', results.length)

            // Normalize results to ensure they have required fields
            const normalizedResults = results.map((item, idx) => ({
                product_id: item.product_id || item.id || `item-${idx}`,
                name: item.name || item.title || 'Unknown Product',
                price: item.price || 0,
                rating: item.rating || 0,
                rating_count: item.rating_count || item.review_count || 0,
                category: item.category || item.main_category || 'Unknown',
                brand: item.brand || 'Unknown',
                image_url: item.image_url || '',
                score: item.score || item.utility || 0.75,
                description: item.description || ''
            }))

            setSearchResult({ ...data, results: normalizedResults })

            // Store metrics
            if (data.metrics) {
                setLastMetrics(data.metrics)
            }

            // Store in history
            useStore.getState().addToHistory({
                query: text,
                budget: searchBudget || budget,
                timestamp: Date.now()
            })

        } catch (err) {
            console.error('❌ Search error:', err)
            setError(err.message || 'An error occurred. Is the backend running on port 8123?')
        } finally {
            setIsLoading(false)
        }
    }, [budget, userId, cart, setLastMetrics])

    // Handle bundle optimization
    const handleOptimize = async () => {
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
                // Update cart with optimized bundle if provided
                console.log('Optimization result:', data)
            }
        } catch (err) {
            console.error('Optimization error:', err)
        }
    }

    // Handle counterfactual budget apply
    const handleApplyBudget = (newBudget) => {
        setBudget(newBudget)
        setShowCounterfactual(false)
    }

    // Get products from search result
    const products = searchResult?.results || searchResult?.bundle?.items || []

    // Quick search suggestions
    const quickSearches = [
        { query: 'Gaming laptop', emoji: '🎮' },
        { query: 'Home office setup', emoji: '🏠' },
        { query: '4K monitor', emoji: '🖥️' },
        { query: 'Wireless headphones', emoji: '🎧' },
        { query: 'Mechanical keyboard', emoji: '⌨️' },
    ]

    return (
        <div className={`min-h-screen ${darkMode ? 'dark' : ''}`}>
            <div className="min-h-screen bg-gradient-to-br from-dark-300 via-dark-200 to-dark-100 text-white">

                {/* Header Bar */}
                <header className="fixed top-0 left-0 right-0 z-40 bg-dark-200/80 backdrop-blur-xl border-b border-white/10">
                    <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                        {/* Logo */}
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-600 
                                          rounded-xl flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <h1 className="text-xl font-bold bg-gradient-to-r from-primary-400 to-primary-300 
                                             bg-clip-text text-transparent">
                                    FinBundle
                                </h1>
                                <p className="text-xs text-white/40">Smart Discovery Engine</p>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex items-center gap-3">
                            {/* Demo Reset */}
                            <button
                                onClick={resetToDemo}
                                className="flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 
                                           rounded-lg text-sm text-white/60 hover:text-white transition-colors"
                                title="Reset to demo state"
                            >
                                <RotateCcw className="w-4 h-4" />
                                <span className="hidden sm:inline">Reset Demo</span>
                            </button>

                            {/* Dark Mode Toggle */}
                            <button
                                onClick={() => setDarkMode(!darkMode)}
                                className="p-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                {darkMode ? (
                                    <Sun className="w-5 h-5 text-amber-400" />
                                ) : (
                                    <Moon className="w-5 h-5 text-primary-400" />
                                )}
                            </button>
                        </div>
                    </div>
                </header>

                {/* Main Content */}
                <main className="pt-24 pb-8">
                    <div className="max-w-7xl mx-auto px-6">

                        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">

                            {/* Left Column - Main Content */}
                            <div className="lg:col-span-3 space-y-8">

                                {/* Hero Section */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    className="text-center py-8"
                                >
                                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                                        Find your perfect <span className="text-primary-400">bundle</span>
                                    </h2>
                                    <p className="text-white/60 max-w-xl mx-auto">
                                        AI-powered product discovery with budget optimization.
                                        Search by text or image.
                                    </p>
                                </motion.div>

                                {/* Search Bar */}
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    transition={{ delay: 0.1 }}
                                >
                                    <MultimodalSearchBar
                                        onSearch={handleSearch}
                                        isLoading={isLoading}
                                    />
                                </motion.div>

                                {/* Quick Search Tags */}
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    transition={{ delay: 0.2 }}
                                    className="flex flex-wrap gap-2 justify-center"
                                >
                                    {quickSearches.map(({ query, emoji }) => (
                                        <button
                                            key={query}
                                            onClick={() => handleSearch({ text: query, budget })}
                                            className="px-4 py-2 bg-white/5 hover:bg-white/10 
                                                     border border-white/10 hover:border-white/20
                                                     rounded-full text-sm text-white/70 hover:text-white 
                                                     transition-all flex items-center gap-2"
                                        >
                                            <span>{emoji}</span>
                                            {query}
                                        </button>
                                    ))}
                                </motion.div>

                                {/* Error Display */}
                                <AnimatePresence>
                                    {error && (
                                        <motion.div
                                            initial={{ opacity: 0, y: -10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0 }}
                                            className="p-4 bg-red-500/20 border border-red-500/50 
                                                       rounded-xl text-red-200"
                                        >
                                            ⚠️ {error}
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* Results Grid */}
                                <AnimatePresence mode="wait">
                                    {products.length > 0 && (
                                        <motion.div
                                            key="results"
                                            initial={{ opacity: 0, y: 20 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            exit={{ opacity: 0, y: -20 }}
                                        >
                                            {/* Results Header */}
                                            <div className="flex items-center justify-between mb-6">
                                                <h3 className="text-lg font-semibold text-white">
                                                    Search Results
                                                    <span className="ml-2 text-sm text-white/50">
                                                        ({products.length} products)
                                                    </span>
                                                </h3>

                                                {searchResult?.metrics && (
                                                    <span className="text-xs text-white/40">
                                                        {searchResult.metrics.path_used?.toUpperCase()} path •
                                                        {Math.round(searchResult.metrics.total_latency_ms)}ms
                                                    </span>
                                                )}
                                            </div>

                                            {/* Product Grid */}
                                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                                                {products.map((product, index) => (
                                                    <motion.div
                                                        key={product.product_id || index}
                                                        initial={{ opacity: 0, y: 20 }}
                                                        animate={{ opacity: 1, y: 0 }}
                                                        transition={{ delay: index * 0.05 }}
                                                    >
                                                        <ProductCard
                                                            product={product}
                                                            onSelect={(p) => console.log('Selected:', p)}
                                                        />
                                                    </motion.div>
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>

                                {/* Empty State */}
                                {!searchResult && !isLoading && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="mt-16 text-center py-12"
                                    >
                                        <div className="text-6xl mb-4">🔍</div>
                                        <h3 className="text-xl font-semibold text-white/80">
                                            Start your search
                                        </h3>
                                        <p className="mt-2 text-white/50 max-w-md mx-auto">
                                            Enter a product name, describe what you're looking for,
                                            or upload an image to find similar items.
                                        </p>
                                    </motion.div>
                                )}

                                {/* Loading State */}
                                {isLoading && (
                                    <motion.div
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        className="py-16 text-center"
                                    >
                                        <motion.div
                                            className="w-16 h-16 border-4 border-primary-500/30 border-t-primary-500 
                                                       rounded-full mx-auto"
                                            animate={{ rotate: 360 }}
                                            transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                                        />
                                        <p className="mt-4 text-white/60">Searching products...</p>
                                    </motion.div>
                                )}
                            </div>

                            {/* Right Column - Sidebar */}
                            <div className="lg:col-span-1 space-y-6">
                                {/* Financial DNA Card */}
                                <FinancialDNACard />

                                {/* Bundle Cart */}
                                <BundleCart
                                    onOptimize={handleOptimize}
                                    onCounterfactual={() => setShowCounterfactual(true)}
                                />
                            </div>
                        </div>
                    </div>
                </main>

                {/* Footer */}
                <footer className="py-8 text-center text-white/40 text-sm border-t border-white/5">
                    Built with ❤️ using{' '}
                    <span className="text-primary-400">Qdrant</span>,{' '}
                    <span className="text-primary-400">Groq</span>, and{' '}
                    <span className="text-primary-400">OR-Tools</span>
                    <br />
                    <span className="text-xs">FinBundle v3 • Smart Commerce Discovery Engine</span>
                </footer>

                {/* Counterfactual Modal */}
                <CounterfactualSlider
                    isOpen={showCounterfactual}
                    onClose={() => setShowCounterfactual(false)}
                    currentQuality={bundleQualityScore || 7.5}
                    onApply={handleApplyBudget}
                />
            </div>
        </div>
    )
}

export default App
