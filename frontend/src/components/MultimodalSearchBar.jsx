import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Loader2, Upload, X, Image as ImageIcon, Gift, Zap, Compass } from 'lucide-react'
import { useStore } from '../store/useStore'

/**
 * MultimodalSearchBar - Enhanced search with text, image, budget, and context
 * 
 * Features:
 * - Text input with suggestions
 * - Image upload with preview
 * - Integrated budget slider
 * - Context toggles (Gift, Urgent, Exploring)
 */
export default function MultimodalSearchBar({ onSearch, isLoading }) {
    const [query, setQuery] = useState('')
    const [imageFile, setImageFile] = useState(null)
    const [imagePreview, setImagePreview] = useState(null)
    const [showBudgetSlider, setShowBudgetSlider] = useState(false)
    const fileInputRef = useRef(null)

    const { budget, setBudget, searchContext, setSearchContext } = useStore()

    // Handle image upload
    const handleImageUpload = (e) => {
        const file = e.target.files?.[0]
        if (file && file.type.startsWith('image/')) {
            setImageFile(file)
            const reader = new FileReader()
            reader.onloadend = () => setImagePreview(reader.result)
            reader.readAsDataURL(file)
        }
    }

    const clearImage = () => {
        setImageFile(null)
        setImagePreview(null)
        if (fileInputRef.current) fileInputRef.current.value = ''
    }

    const handleSubmit = (e) => {
        e.preventDefault()
        if ((query.trim() || imageFile) && !isLoading) {
            onSearch({
                text: query,
                image: imageFile,
                budget,
                context: searchContext
            })
        }
    }

    const contextOptions = [
        { id: 'gift', icon: Gift, label: 'Gift Mode', color: 'text-pink-400' },
        { id: 'urgent', icon: Zap, label: 'Urgent', color: 'text-amber-400' },
        { id: 'exploring', icon: Compass, label: 'Exploring', color: 'text-cyan-400' },
    ]

    return (
        <div className="space-y-4">
            {/* Main Search Form */}
            <form onSubmit={handleSubmit} className="relative">
                <div className="relative flex items-center">
                    {/* Search Icon */}
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40 z-10" />

                    {/* Text Input */}
                    <input
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="What are you looking for? e.g., gaming laptop, home office setup..."
                        className="w-full pl-14 pr-44 py-4 bg-white/5 border border-white/10 rounded-2xl
                                   text-white placeholder-white/40 focus:outline-none focus:border-primary-500/50
                                   focus:ring-2 focus:ring-primary-500/20 transition-all"
                        disabled={isLoading}
                    />

                    {/* Action Buttons */}
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
                        {/* Image Upload Button */}
                        <motion.button
                            type="button"
                            onClick={() => fileInputRef.current?.click()}
                            className={`p-2.5 rounded-xl transition-all ${imagePreview
                                    ? 'bg-primary-500/20 text-primary-400'
                                    : 'bg-white/5 text-white/50 hover:bg-white/10 hover:text-white/70'
                                }`}
                            whileHover={{ scale: 1.05 }}
                            whileTap={{ scale: 0.95 }}
                            title="Upload image to search visually"
                        >
                            <ImageIcon className="w-5 h-5" />
                        </motion.button>

                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleImageUpload}
                            className="hidden"
                        />

                        {/* Search Button */}
                        <motion.button
                            type="submit"
                            disabled={isLoading || (!query.trim() && !imageFile)}
                            className="px-5 py-2.5 bg-gradient-to-r from-primary-500 to-primary-600 
                                       text-white font-medium rounded-xl disabled:opacity-50 
                                       disabled:cursor-not-allowed shadow-lg shadow-primary-500/25"
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
                </div>
            </form>

            {/* Image Preview */}
            <AnimatePresence>
                {imagePreview && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="flex items-center gap-3 p-3 bg-white/5 border border-white/10 rounded-xl"
                    >
                        <div className="relative">
                            <img
                                src={imagePreview}
                                alt="Search reference"
                                className="w-16 h-16 object-cover rounded-lg"
                            />
                            <button
                                onClick={clearImage}
                                className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full 
                                           text-white hover:bg-red-600 transition-colors"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </div>
                        <div>
                            <p className="text-sm text-white/80">Visual search enabled</p>
                            <p className="text-xs text-white/50">Finding products that match this image</p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Budget & Context Row */}
            <div className="flex flex-wrap items-center gap-4">
                {/* Budget Slider Toggle */}
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setShowBudgetSlider(!showBudgetSlider)}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${showBudgetSlider
                                ? 'bg-primary-500/20 text-primary-400 border border-primary-500/30'
                                : 'bg-white/5 text-white/60 border border-white/10 hover:bg-white/10'
                            }`}
                    >
                        💰 Budget: ${budget}
                    </button>

                    {/* Inline Budget Slider */}
                    <AnimatePresence>
                        {showBudgetSlider && (
                            <motion.div
                                initial={{ opacity: 0, width: 0 }}
                                animate={{ opacity: 1, width: 200 }}
                                exit={{ opacity: 0, width: 0 }}
                                className="flex items-center gap-2 overflow-hidden"
                            >
                                <span className="text-xs text-white/40">$100</span>
                                <input
                                    type="range"
                                    min="100"
                                    max="5000"
                                    step="50"
                                    value={budget}
                                    onChange={(e) => setBudget(Number(e.target.value))}
                                    className="w-32 accent-primary-500"
                                />
                                <span className="text-xs text-white/40">$5K</span>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>

                {/* Divider */}
                <div className="w-px h-6 bg-white/10" />

                {/* Context Toggles */}
                <div className="flex items-center gap-2">
                    {contextOptions.map(({ id, icon: Icon, label, color }) => (
                        <motion.button
                            key={id}
                            onClick={() => setSearchContext(
                                searchContext === id ? null : id
                            )}
                            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm 
                                       transition-all ${searchContext === id
                                    ? `bg-white/10 ${color} border border-white/20`
                                    : 'text-white/50 hover:text-white/70 hover:bg-white/5'
                                }`}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                        >
                            <Icon className="w-4 h-4" />
                            <span className="hidden sm:inline">{label}</span>
                        </motion.button>
                    ))}
                </div>
            </div>
        </div>
    )
}
