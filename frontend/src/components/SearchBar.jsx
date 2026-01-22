import { useState } from 'react'
import { motion } from 'framer-motion'
import { Search, Loader2 } from 'lucide-react'

export default function SearchBar({ onSearch, isLoading }) {
    const [query, setQuery] = useState('')

    const handleSubmit = (e) => {
        e.preventDefault()
        if (query.trim() && !isLoading) {
            onSearch(query)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="relative">
            <div className="relative">
                <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="What are you looking for? e.g., gaming laptop, home office setup..."
                    className="input-search pl-14 pr-32"
                    disabled={isLoading}
                />
                <motion.button
                    type="submit"
                    disabled={isLoading || !query.trim()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-2"
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                >
                    {isLoading ? (
                        <span className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            Searching...
                        </span>
                    ) : (
                        'Search'
                    )}
                </motion.button>
            </div>
        </form>
    )
}
