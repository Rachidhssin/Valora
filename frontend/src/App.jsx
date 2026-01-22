import { useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Header from './components/Header'
import SearchBar from './components/SearchBar'
import SearchResults from './components/SearchResults'
import Sidebar from './components/Sidebar'
import { useStore } from './store/useStore'

function App() {
    const [searchResult, setSearchResult] = useState(null)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)

    const { budget, userId, cart } = useStore()

    const handleSearch = useCallback(async (query) => {
        if (!query.trim()) return

        setIsLoading(true)
        setError(null)

        try {
            const response = await fetch('/api/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query,
                    budget,
                    user_id: userId,
                    cart
                })
            })

            if (!response.ok) {
                throw new Error('Search failed')
            }

            const data = await response.json()
            setSearchResult(data)

            // Store in history
            useStore.getState().addToHistory({ query, budget, timestamp: Date.now() })

        } catch (err) {
            setError(err.message || 'An error occurred')
            console.error('Search error:', err)
        } finally {
            setIsLoading(false)
        }
    }, [budget, userId, cart])

    return (
        <div className="min-h-screen flex">
            {/* Sidebar */}
            <Sidebar />

            {/* Main Content */}
            <main className="flex-1 ml-72">
                <div className="max-w-6xl mx-auto px-8 py-8">
                    {/* Header */}
                    <Header />

                    {/* Search Section */}
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="mt-8"
                    >
                        <SearchBar onSearch={handleSearch} isLoading={isLoading} />
                    </motion.div>

                    {/* Quick Search Tags */}
                    <div className="mt-6 flex flex-wrap gap-3">
                        {['Gaming laptop', 'Home office setup', 'Budget keyboard', '4K monitor', 'Complete gaming rig'].map((term) => (
                            <button
                                key={term}
                                onClick={() => handleSearch(term)}
                                className="px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 
                         rounded-full text-sm text-white/70 hover:text-white transition-all"
                            >
                                {term}
                            </button>
                        ))}
                    </div>

                    {/* Error Display */}
                    <AnimatePresence>
                        {error && (
                            <motion.div
                                initial={{ opacity: 0, y: -10 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                                className="mt-6 p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-200"
                            >
                                ⚠️ {error}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Results */}
                    <AnimatePresence mode="wait">
                        {searchResult && (
                            <motion.div
                                key="results"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                                className="mt-8"
                            >
                                <SearchResults result={searchResult} />
                            </motion.div>
                        )}
                    </AnimatePresence>

                    {/* Empty State */}
                    {!searchResult && !isLoading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            className="mt-16 text-center"
                        >
                            <div className="text-6xl mb-4">🔍</div>
                            <h3 className="text-xl font-semibold text-white/80">Start your search</h3>
                            <p className="mt-2 text-white/50">
                                Enter a product or describe what you're looking for
                            </p>
                        </motion.div>
                    )}
                </div>

                {/* Footer */}
                <footer className="mt-16 py-8 text-center text-white/40 text-sm">
                    Built with ❤️ using <span className="text-primary-400">Qdrant</span>, <span className="text-primary-400">Groq</span>, and <span className="text-primary-400">OR-Tools</span>
                    <br />
                    <span className="text-xs">FinBundle v3 • Smart Commerce Discovery Engine</span>
                </footer>
            </main>
        </div>
    )
}

export default App
