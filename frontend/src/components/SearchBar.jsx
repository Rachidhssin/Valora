import { useState, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Loader2, ImagePlus, X, Camera } from 'lucide-react'

export default function SearchBar({ onSearch, onImageSearch, isLoading }) {
    const [query, setQuery] = useState('')
    const [imagePreview, setImagePreview] = useState(null)
    const [imageBase64, setImageBase64] = useState(null)
    const [isDragging, setIsDragging] = useState(false)
    const fileInputRef = useRef(null)

    const handleSubmit = (e) => {
        e.preventDefault()
        if (isLoading) return
        
        if (imageBase64 && onImageSearch) {
            // Image search (with optional text query)
            onImageSearch(imageBase64, query.trim() || null)
        } else if (query.trim()) {
            // Text-only search
            onSearch(query)
        }
    }

    const handleImageSelect = (file) => {
        if (!file || !file.type.startsWith('image/')) return
        
        // Preview
        const reader = new FileReader()
        reader.onload = (e) => {
            setImagePreview(e.target.result)
            // Extract base64 (remove data URL prefix for API)
            setImageBase64(e.target.result)
        }
        reader.readAsDataURL(file)
    }

    const handleFileInput = (e) => {
        const file = e.target.files?.[0]
        if (file) handleImageSelect(file)
    }

    const handleDrop = (e) => {
        e.preventDefault()
        setIsDragging(false)
        const file = e.dataTransfer.files?.[0]
        if (file) handleImageSelect(file)
    }

    const handleDragOver = (e) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const handleDragLeave = (e) => {
        e.preventDefault()
        setIsDragging(false)
    }

    const clearImage = () => {
        setImagePreview(null)
        setImageBase64(null)
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const canSearch = query.trim() || imageBase64

    return (
        <form onSubmit={handleSubmit} className="relative">
            {/* Image Preview */}
            <AnimatePresence>
                {imagePreview && (
                    <motion.div
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="mb-3 flex items-center gap-3 p-3 bg-white/5 rounded-xl border border-white/10"
                    >
                        <div className="relative">
                            <img
                                src={imagePreview}
                                alt="Search by image"
                                className="w-16 h-16 object-cover rounded-lg"
                            />
                            <button
                                type="button"
                                onClick={clearImage}
                                className="absolute -top-2 -right-2 p-1 bg-red-500 rounded-full hover:bg-red-600 transition-colors"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </div>
                        <div className="flex-1">
                            <p className="text-sm font-medium text-white">Image uploaded</p>
                            <p className="text-xs text-white/60">
                                Add text to refine your search, or search by image only
                            </p>
                        </div>
                        <div className="flex items-center gap-1 px-2 py-1 bg-accent-500/20 rounded-lg">
                            <Camera className="w-3.5 h-3.5 text-accent-400" />
                            <span className="text-xs text-accent-400">Visual Search</span>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Search Input with Image Upload */}
            <div
                className={`relative transition-all ${isDragging ? 'ring-2 ring-accent-500 ring-offset-2 ring-offset-dark-900 rounded-2xl' : ''}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
            >
                {/* Drag overlay */}
                <AnimatePresence>
                    {isDragging && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-accent-500/20 rounded-2xl flex items-center justify-center z-10 pointer-events-none"
                        >
                            <div className="flex items-center gap-2 text-accent-400">
                                <ImagePlus className="w-6 h-6" />
                                <span className="font-medium">Drop image here</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Image upload button */}
                <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="absolute left-4 top-1/2 -translate-y-1/2 p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors group"
                    title="Upload image to search visually"
                >
                    <ImagePlus className="w-5 h-5 text-white/40 group-hover:text-accent-400 transition-colors" />
                </button>
                
                <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    onChange={handleFileInput}
                    className="hidden"
                />

                <Search className="absolute left-16 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40" />
                <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder={imageBase64 
                        ? "Add text to refine image search (optional)..." 
                        : "Search products or drop an image..."
                    }
                    className="w-full bg-dark-800 border border-white/10 rounded-2xl py-4 pl-24 pr-32 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-accent-500 focus:border-transparent transition-all"
                    disabled={isLoading}
                />
                <motion.button
                    type="submit"
                    disabled={isLoading || !canSearch}
                    className="absolute right-2 top-1/2 -translate-y-1/2 btn-primary py-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    whileHover={{ scale: canSearch ? 1.02 : 1 }}
                    whileTap={{ scale: canSearch ? 0.98 : 1 }}
                >
                    {isLoading ? (
                        <span className="flex items-center gap-2">
                            <Loader2 className="w-4 h-4 animate-spin" />
                            {imageBase64 ? 'Analyzing...' : 'Searching...'}
                        </span>
                    ) : (
                        <span className="flex items-center gap-2">
                            {imageBase64 && <Camera className="w-4 h-4" />}
                            Search
                        </span>
                    )}
                </motion.button>
            </div>

            {/* Help text */}
            {!imagePreview && (
                <p className="mt-2 text-xs text-white/40 text-center">
                    💡 Tip: Drop or upload an image of a product to find similar items
                </p>
            )}
        </form>
    )
}
