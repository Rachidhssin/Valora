import { useEffect, useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Package, Zap, Brain, Target, Sparkles, ShoppingCart, Clock, AlertCircle, Eye, Filter, Check, Plus, Star, ChevronDown, ChevronUp, Layers, DollarSign, TrendingUp, X, Info, Award, Tag, Cpu, Monitor, HardDrive, MemoryStick, Wifi, Battery, Gauge, Palette, Volume2, Camera, Smartphone, Keyboard, Mouse, Headphones, Tv, Speaker } from 'lucide-react'
import { useStore } from '../store/useStore'

// ============================================================================
// SPECIFICATION EXTRACTOR - Parse product names/descriptions for specs
// ============================================================================
function extractProductSpecs(product) {
    const name = (product.name || '').toLowerCase()
    const description = (product.description || '').toLowerCase()
    const text = `${name} ${description}`
    
    const specs = {}
    
    // === DISPLAY SPECS ===
    // Screen size: 15.6", 27", 32" etc
    const screenMatch = text.match(/(\d{1,2}(?:\.\d)?)["\s-]*(?:inch|in\b|"|'')/i)
    if (screenMatch) specs.screenSize = `${screenMatch[1]}"`
    
    // Resolution: 4K, 1080p, FHD, QHD, UHD
    if (text.includes('4k') || text.includes('uhd') || text.includes('2160p')) specs.resolution = '4K UHD'
    else if (text.includes('1440p') || text.includes('qhd') || text.includes('wqhd')) specs.resolution = 'QHD 1440p'
    else if (text.includes('1080p') || text.includes('fhd') || text.includes('full hd')) specs.resolution = 'Full HD 1080p'
    else if (text.includes('720p') || text.includes('hd')) specs.resolution = 'HD 720p'
    
    // Refresh rate: 60Hz, 120Hz, 144Hz, 240Hz, 360Hz
    const refreshMatch = text.match(/(\d{2,3})\s*hz/i)
    if (refreshMatch) specs.refreshRate = `${refreshMatch[1]}Hz`
    
    // Panel type: IPS, VA, OLED, TN
    if (text.includes('oled')) specs.panelType = 'OLED'
    else if (text.includes('ips')) specs.panelType = 'IPS'
    else if (text.includes(' va ') || text.includes('-va')) specs.panelType = 'VA'
    else if (text.includes(' tn ')) specs.panelType = 'TN'
    
    // === PROCESSOR ===
    // Intel processors
    const intelMatch = text.match(/(?:intel\s+)?(?:core\s+)?(i[3579])[- ]?(\d{4,5}[a-z]*)/i)
    if (intelMatch) specs.processor = `Intel Core ${intelMatch[1].toUpperCase()}-${intelMatch[2].toUpperCase()}`
    
    // AMD Ryzen
    const ryzenMatch = text.match(/ryzen\s*([3579])\s*(\d{4}[a-z]*)/i)
    if (ryzenMatch) specs.processor = `AMD Ryzen ${ryzenMatch[1]} ${ryzenMatch[2].toUpperCase()}`
    
    // Apple M-series
    const appleMatch = text.match(/\b(m[123])\s*(pro|max|ultra)?\b/i)
    if (appleMatch) specs.processor = `Apple ${appleMatch[1].toUpperCase()}${appleMatch[2] ? ' ' + appleMatch[2].charAt(0).toUpperCase() + appleMatch[2].slice(1) : ''}`
    
    // === MEMORY (RAM) ===
    const ramMatch = text.match(/(\d{1,3})\s*gb\s*(?:ddr[45]?\s*)?(?:ram|memory|sdram)/i) ||
                     text.match(/(?:ram|memory)[:\s]*(\d{1,3})\s*gb/i) ||
                     text.match(/(\d{1,3})\s*gb\s*ddr[45]/i)
    if (ramMatch) specs.ram = `${ramMatch[1]}GB RAM`
    
    // === STORAGE ===
    // SSD
    const ssdMatch = text.match(/(\d{3,4})\s*gb\s*(?:nvme\s*)?ssd/i) ||
                     text.match(/(\d+(?:\.\d)?)\s*tb\s*(?:nvme\s*)?ssd/i)
    if (ssdMatch) {
        const size = ssdMatch[1]
        specs.storage = size.includes('.') || parseInt(size) <= 8 ? `${size}TB SSD` : `${size}GB SSD`
    }
    
    // HDD
    const hddMatch = text.match(/(\d+)\s*tb\s*hdd/i) || text.match(/(\d{3,4})\s*gb\s*hdd/i)
    if (hddMatch) {
        const size = hddMatch[1]
        const hddSpec = parseInt(size) >= 1000 || text.includes('tb') ? `${size}TB HDD` : `${size}GB HDD`
        specs.storage = specs.storage ? `${specs.storage} + ${hddSpec}` : hddSpec
    }
    
    // === GRAPHICS ===
    // NVIDIA RTX/GTX
    const nvidiaMatch = text.match(/(?:nvidia\s*)?(?:geforce\s*)?(rtx|gtx)\s*(\d{4})\s*(ti|super)?/i)
    if (nvidiaMatch) specs.graphics = `NVIDIA ${nvidiaMatch[1].toUpperCase()} ${nvidiaMatch[2]}${nvidiaMatch[3] ? ' ' + nvidiaMatch[3].toUpperCase() : ''}`
    
    // AMD Radeon
    const radeonMatch = text.match(/(?:amd\s*)?radeon\s*(rx|vega)?\s*(\d{3,4})/i)
    if (radeonMatch) specs.graphics = `AMD Radeon ${radeonMatch[1] ? radeonMatch[1].toUpperCase() + ' ' : ''}${radeonMatch[2]}`
    
    // === CONNECTIVITY ===
    if (text.includes('wifi 6e') || text.includes('wi-fi 6e')) specs.wifi = 'WiFi 6E'
    else if (text.includes('wifi 6') || text.includes('wi-fi 6')) specs.wifi = 'WiFi 6'
    else if (text.includes('wifi') || text.includes('wi-fi') || text.includes('wireless')) specs.wifi = 'WiFi'
    
    if (text.includes('bluetooth 5')) specs.bluetooth = 'Bluetooth 5.0+'
    else if (text.includes('bluetooth')) specs.bluetooth = 'Bluetooth'
    
    if (text.includes('usb-c') || text.includes('usb c') || text.includes('type-c')) specs.usbc = 'USB-C'
    if (text.includes('thunderbolt')) specs.thunderbolt = 'Thunderbolt'
    if (text.includes('hdmi 2.1')) specs.hdmi = 'HDMI 2.1'
    else if (text.includes('hdmi')) specs.hdmi = 'HDMI'
    
    // === AUDIO ===
    if (text.includes('noise cancel') || text.includes('anc')) specs.audio = 'Active Noise Cancelling'
    if (text.includes('dolby atmos')) specs.dolbyAtmos = 'Dolby Atmos'
    if (text.includes('hi-res') || text.includes('hires') || text.includes('high-res')) specs.hiRes = 'Hi-Res Audio'
    
    // Drivers (headphones/speakers)
    const driverMatch = text.match(/(\d{2,3})\s*mm\s*driver/i)
    if (driverMatch) specs.drivers = `${driverMatch[1]}mm Drivers`
    
    // Frequency response
    const freqMatch = text.match(/(\d{1,2})\s*hz?\s*[-–]\s*(\d{2,3})\s*khz/i)
    if (freqMatch) specs.frequency = `${freqMatch[1]}Hz - ${freqMatch[2]}kHz`
    
    // === KEYBOARD/MOUSE ===
    if (text.includes('mechanical')) specs.keyType = 'Mechanical'
    if (text.includes('rgb') || text.includes('backlit')) specs.lighting = 'RGB Backlit'
    
    // DPI for mouse
    const dpiMatch = text.match(/(\d{3,5})\s*dpi/i)
    if (dpiMatch) specs.dpi = `${parseInt(dpiMatch[1]).toLocaleString()} DPI`
    
    // === CAMERA ===
    // Megapixels
    const mpMatch = text.match(/(\d{1,3})\s*mp/i) || text.match(/(\d{1,3})\s*megapixel/i)
    if (mpMatch) specs.megapixels = `${mpMatch[1]}MP`
    
    // Camera resolution (webcam)
    if (text.includes('4k')) specs.cameraRes = '4K'
    else if (text.includes('1080p') || text.includes('full hd')) specs.cameraRes = '1080p'
    else if (text.includes('720p')) specs.cameraRes = '720p'
    
    // === BATTERY ===
    const batteryMatch = text.match(/(\d{2,3})\s*wh/i)
    if (batteryMatch) specs.battery = `${batteryMatch[1]}Wh`
    
    const batteryHoursMatch = text.match(/(\d{1,2})\s*(?:hour|hr)s?\s*battery/i)
    if (batteryHoursMatch) specs.batteryLife = `${batteryHoursMatch[1]}h Battery Life`
    
    // === WEIGHT ===
    const weightKgMatch = text.match(/(\d+(?:\.\d+)?)\s*kg/i)
    if (weightKgMatch) specs.weight = `${weightKgMatch[1]}kg`
    
    const weightLbMatch = text.match(/(\d+(?:\.\d+)?)\s*(?:lb|lbs|pounds)/i)
    if (weightLbMatch) specs.weight = `${weightLbMatch[1]}lbs`
    
    // === OS ===
    if (text.includes('windows 11')) specs.os = 'Windows 11'
    else if (text.includes('windows 10')) specs.os = 'Windows 10'
    else if (text.includes('macos') || text.includes('mac os')) specs.os = 'macOS'
    else if (text.includes('chrome os') || text.includes('chromeos')) specs.os = 'Chrome OS'
    
    // === SPECIAL FEATURES ===
    if (text.includes('touchscreen') || text.includes('touch screen')) specs.touchscreen = 'Touchscreen'
    if (text.includes('2-in-1') || text.includes('convertible')) specs.formFactor = '2-in-1 Convertible'
    if (text.includes('gaming')) specs.category = 'Gaming'
    if (text.includes('creator') || text.includes('content creation')) specs.category = 'Creator'
    
    return specs
}

// Get icon for a spec type
function getSpecIcon(specKey) {
    const icons = {
        screenSize: Monitor,
        resolution: Tv,
        refreshRate: Gauge,
        panelType: Monitor,
        processor: Cpu,
        ram: MemoryStick,
        storage: HardDrive,
        graphics: Palette,
        wifi: Wifi,
        bluetooth: Wifi,
        usbc: Cpu,
        thunderbolt: Zap,
        hdmi: Tv,
        audio: Volume2,
        dolbyAtmos: Volume2,
        hiRes: Volume2,
        drivers: Headphones,
        frequency: Volume2,
        keyType: Keyboard,
        lighting: Sparkles,
        dpi: Mouse,
        megapixels: Camera,
        cameraRes: Camera,
        battery: Battery,
        batteryLife: Battery,
        weight: Package,
        os: Monitor,
        touchscreen: Smartphone,
        formFactor: Monitor,
        category: Tag
    }
    return icons[specKey] || Info
}

// Get display label for a spec
function getSpecLabel(specKey) {
    const labels = {
        screenSize: 'Display',
        resolution: 'Resolution',
        refreshRate: 'Refresh Rate',
        panelType: 'Panel',
        processor: 'Processor',
        ram: 'Memory',
        storage: 'Storage',
        graphics: 'Graphics',
        wifi: 'WiFi',
        bluetooth: 'Bluetooth',
        usbc: 'USB-C',
        thunderbolt: 'Thunderbolt',
        hdmi: 'HDMI',
        audio: 'Audio',
        dolbyAtmos: 'Dolby Atmos',
        hiRes: 'Hi-Res',
        drivers: 'Drivers',
        frequency: 'Frequency',
        keyType: 'Keys',
        lighting: 'Lighting',
        dpi: 'Sensitivity',
        megapixels: 'Resolution',
        cameraRes: 'Video',
        battery: 'Battery',
        batteryLife: 'Battery Life',
        weight: 'Weight',
        os: 'System',
        touchscreen: 'Touch',
        formFactor: 'Form Factor',
        category: 'Type'
    }
    return labels[specKey] || specKey
}

// ============================================================================
// PRODUCT INFO MODAL - Flowing background animation with detailed product info
// ============================================================================
function ProductInfoModal({ product, explanation, isOpen, onClose, onAddToCart, isInCart }) {
    if (!isOpen || !product) return null
    
    // Extract specifications from product name/description
    const specs = useMemo(() => extractProductSpecs(product), [product])
    
    // Extract all available product details
    const {
        name = 'Unknown Product',
        brand = '',
        price = 0,
        rating = 0,
        rating_count = 0,
        category = '',
        description = '',
        image_url = '',
        utility = 0,
        score = 0,
        is_recommended = false,
        in_stock = true,
        condition = 'new',
        match_tier = '',
        product_id = '',
        id = '',
        _scoring = {}
    } = product
    
    const productId = product_id || id
    const matchScore = utility || score || (_scoring?.final_score) || 0
    
    return (
        <AnimatePresence>
            {isOpen && (
                <>
                    {/* Backdrop with flowing gradient animation */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="fixed inset-0 z-50 overflow-hidden"
                    >
                        {/* Animated flowing background */}
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-md" />
                        <div className="absolute inset-0 overflow-hidden">
                            <motion.div
                                animate={{
                                    x: [0, 100, 0, -100, 0],
                                    y: [0, -50, 100, -50, 0],
                                    scale: [1, 1.2, 1, 1.1, 1],
                                }}
                                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                                className="absolute -top-1/2 -left-1/2 w-[200%] h-[200%] bg-gradient-conic from-violet-500/20 via-purple-500/10 to-cyan-500/20 blur-3xl"
                            />
                            <motion.div
                                animate={{
                                    x: [0, -80, 0, 80, 0],
                                    y: [0, 80, -50, 80, 0],
                                }}
                                transition={{ duration: 15, repeat: Infinity, ease: "linear" }}
                                className="absolute top-1/4 right-0 w-96 h-96 bg-gradient-to-br from-pink-500/30 to-transparent rounded-full blur-3xl"
                            />
                            <motion.div
                                animate={{
                                    x: [0, 60, 0, -60, 0],
                                    y: [0, -40, 60, -40, 0],
                                }}
                                transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
                                className="absolute bottom-0 left-1/4 w-80 h-80 bg-gradient-to-tr from-blue-500/30 to-transparent rounded-full blur-3xl"
                            />
                        </div>
                    </motion.div>
                    
                    {/* Modal Content */}
                    <motion.div
                        initial={{ opacity: 0, scale: 0.9, y: 20 }}
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.9, y: 20 }}
                        transition={{ type: "spring", damping: 25, stiffness: 300 }}
                        className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none"
                    >
                        <div 
                            onClick={(e) => e.stopPropagation()}
                            className="relative w-full max-w-3xl max-h-[90vh] overflow-y-auto pointer-events-auto
                                     bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800
                                     border border-white/10 rounded-3xl shadow-2xl shadow-violet-500/20"
                        >
                            {/* Close button */}
                            <button
                                onClick={onClose}
                                className="absolute top-4 right-4 p-2 rounded-full bg-black/50 hover:bg-white/20 
                                         transition-colors z-20 backdrop-blur-sm"
                            >
                                <X className="w-5 h-5 text-white" />
                            </button>
                            
                            {/* Two Column Layout */}
                            <div className="flex flex-col md:flex-row">
                                {/* Left: Product Image */}
                                <div className="relative w-full md:w-2/5 h-64 md:h-auto md:min-h-[400px] bg-gradient-to-br from-violet-500/10 to-purple-500/5 overflow-hidden rounded-t-3xl md:rounded-l-3xl md:rounded-tr-none">
                                    {image_url ? (
                                        <img 
                                            src={image_url} 
                                            alt={name}
                                            className="w-full h-full object-contain p-6"
                                            onError={(e) => e.target.style.display = 'none'}
                                        />
                                    ) : (
                                        <div className="w-full h-full flex items-center justify-center">
                                            <Package className="w-24 h-24 text-white/20" />
                                        </div>
                                    )}
                                    
                                    {/* Badges */}
                                    <div className="absolute top-4 left-4 flex flex-col gap-2">
                                        {is_recommended && (
                                            <div className="px-3 py-1.5 bg-gradient-to-r from-violet-500 to-purple-600 
                                                          rounded-full text-xs font-bold text-white flex items-center gap-1 shadow-lg">
                                                <Sparkles className="w-3 h-3" />
                                                AI Pick
                                            </div>
                                        )}
                                        {match_tier === 'primary' && (
                                            <div className="px-3 py-1.5 bg-emerald-500/90
                                                          rounded-full text-xs font-bold text-white flex items-center gap-1 shadow-lg">
                                                <Check className="w-3 h-3" />
                                                Best Match
                                            </div>
                                        )}
                                    </div>
                                </div>
                                
                                {/* Right: Product Details */}
                                <div className="flex-1 p-6 space-y-4">
                                    {/* Brand */}
                                    {brand && (
                                        <p className="text-sm font-semibold text-violet-400 uppercase tracking-wider">
                                            {brand}
                                        </p>
                                    )}
                                    
                                    {/* Name */}
                                    <h2 className="text-xl md:text-2xl font-bold text-white leading-tight">
                                        {name}
                                    </h2>
                                    
                                    {/* Price Row */}
                                    <div className="flex items-center gap-4 flex-wrap">
                                        <div className="text-3xl font-bold text-white">
                                            ${typeof price === 'number' ? price.toFixed(2) : price}
                                        </div>
                                        {in_stock !== false ? (
                                            <span className="px-2 py-1 bg-green-500/20 text-green-400 text-xs font-medium rounded-full">
                                                In Stock
                                            </span>
                                        ) : (
                                            <span className="px-2 py-1 bg-red-500/20 text-red-400 text-xs font-medium rounded-full">
                                                Out of Stock
                                            </span>
                                        )}
                                        {condition && condition !== 'new' && (
                                            <span className="px-2 py-1 bg-amber-500/20 text-amber-400 text-xs font-medium rounded-full capitalize">
                                                {condition}
                                            </span>
                                        )}
                                    </div>
                                    
                                    {/* Rating */}
                                    {rating > 0 && (
                                        <div className="flex items-center gap-3">
                                            <div className="flex items-center gap-1">
                                                {[1, 2, 3, 4, 5].map((star) => (
                                                    <Star 
                                                        key={star}
                                                        className={`w-5 h-5 ${star <= Math.round(rating) ? 'text-amber-400 fill-amber-400' : 'text-gray-600'}`}
                                                    />
                                                ))}
                                            </div>
                                            <span className="font-semibold text-white">{rating.toFixed(1)}</span>
                                            {rating_count > 0 && (
                                                <span className="text-sm text-white/50">({rating_count.toLocaleString()} reviews)</span>
                                            )}
                                        </div>
                                    )}
                                    
                                    {/* Tags Row */}
                                    <div className="flex flex-wrap gap-2">
                                        {category && (
                                            <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-sm text-white/70 flex items-center gap-2">
                                                <Tag className="w-3 h-3" />
                                                {category.replace(/_/g, ' ')}
                                            </span>
                                        )}
                                        {matchScore > 0 && (
                                            <span className="px-3 py-1.5 bg-green-500/10 border border-green-500/30 rounded-full text-sm text-green-400 flex items-center gap-2">
                                                <TrendingUp className="w-3 h-3" />
                                                {(matchScore * 100).toFixed(0)}% match
                                            </span>
                                        )}
                                        {productId && (
                                            <span className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-full text-xs text-white/40">
                                                ID: {productId.slice(0, 10)}...
                                            </span>
                                        )}
                                    </div>
                                    
                                    {/* Extracted Specifications */}
                                    {Object.keys(specs).length > 0 && (
                                        <motion.div
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.15 }}
                                            className="p-4 bg-gradient-to-br from-blue-500/10 via-purple-500/5 to-pink-500/10 rounded-xl border border-white/10"
                                        >
                                            <h4 className="text-xs font-semibold text-white/70 uppercase mb-3 flex items-center gap-2">
                                                <Cpu className="w-4 h-4 text-blue-400" />
                                                Key Specifications
                                            </h4>
                                            <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                                                {Object.entries(specs).map(([key, value]) => {
                                                    const IconComponent = getSpecIcon(key)
                                                    return (
                                                        <div key={key} className="flex items-start gap-2 text-sm">
                                                            <IconComponent className="w-4 h-4 text-violet-400 shrink-0 mt-0.5" />
                                                            <div className="flex flex-col min-w-0">
                                                                <span className="text-white/40 text-xs">{getSpecLabel(key)}</span>
                                                                <span className="text-white font-medium text-sm truncate">{value}</span>
                                                            </div>
                                                        </div>
                                                    )
                                                })}
                                            </div>
                                        </motion.div>
                                    )}
                                    
                                    {/* Scoring Details */}
                                    {_scoring && Object.keys(_scoring).length > 0 && (
                                        <div className="p-3 bg-white/5 rounded-xl border border-white/10">
                                            <h4 className="text-xs font-semibold text-white/50 uppercase mb-2">AI Scoring Breakdown</h4>
                                            <div className="grid grid-cols-2 gap-2 text-sm">
                                                {_scoring.semantic_score !== undefined && (
                                                    <div className="flex justify-between">
                                                        <span className="text-white/50">Relevance</span>
                                                        <span className="text-white font-medium">{(_scoring.semantic_score * 100).toFixed(0)}%</span>
                                                    </div>
                                                )}
                                                {_scoring.quality_score !== undefined && (
                                                    <div className="flex justify-between">
                                                        <span className="text-white/50">Quality</span>
                                                        <span className="text-white font-medium">{(_scoring.quality_score * 100).toFixed(0)}%</span>
                                                    </div>
                                                )}
                                                {_scoring.price_score !== undefined && (
                                                    <div className="flex justify-between">
                                                        <span className="text-white/50">Value</span>
                                                        <span className="text-white font-medium">{(_scoring.price_score * 100).toFixed(0)}%</span>
                                                    </div>
                                                )}
                                                {_scoring.afig_score !== undefined && (
                                                    <div className="flex justify-between">
                                                        <span className="text-white/50">Profile Fit</span>
                                                        <span className="text-white font-medium">{(_scoring.afig_score * 100).toFixed(0)}%</span>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    )}
                                    
                                    {/* AI Explanation */}
                                    {explanation && (
                                        <motion.div
                                            initial={{ opacity: 0, y: 10 }}
                                            animate={{ opacity: 1, y: 0 }}
                                            transition={{ delay: 0.2 }}
                                            className="p-4 bg-gradient-to-r from-violet-500/10 via-purple-500/10 to-pink-500/10 
                                                     border border-violet-500/20 rounded-xl"
                                        >
                                            <div className="flex items-start gap-3">
                                                <div className="p-2 bg-violet-500/20 rounded-lg shrink-0">
                                                    <Brain className="w-5 h-5 text-violet-400" />
                                                </div>
                                                <div>
                                                    <h4 className="font-semibold text-violet-300 mb-1">Why This Product?</h4>
                                                    <p className="text-sm text-white/70 leading-relaxed">{explanation}</p>
                                                </div>
                                            </div>
                                        </motion.div>
                                    )}
                                    
                                    {/* Product Description */}
                                    {description && description.length > 5 && (
                                        <div>
                                            <h4 className="font-semibold text-white/80 mb-2 flex items-center gap-2 text-sm">
                                                <Info className="w-4 h-4" /> Description
                                            </h4>
                                            <p className="text-sm text-white/60 leading-relaxed line-clamp-4">{description}</p>
                                        </div>
                                    )}
                                    
                                    {/* Action Buttons */}
                                    <div className="flex gap-3 pt-2">
                                        <motion.button
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                            onClick={(e) => {
                                                if (!isInCart) {
                                                    // Get button position for animation with product details
                                                    const rect = e.currentTarget.getBoundingClientRect()
                                                    window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
                                                        detail: {
                                                            x: rect.left + rect.width / 2,
                                                            y: rect.top + rect.height / 2,
                                                            productImage: product.image_url || product.image,
                                                            productName: product.name,
                                                            productPrice: product.price
                                                        }
                                                    }))
                                                }
                                                onAddToCart(product)
                                            }}
                                            disabled={isInCart}
                                            className={`flex-1 py-3 px-6 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all
                                                ${isInCart 
                                                    ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                                    : 'bg-gradient-to-r from-violet-500 to-purple-600 text-white shadow-lg shadow-violet-500/30 hover:shadow-violet-500/50'
                                                }`}
                                        >
                                            {isInCart ? (
                                                <><Check className="w-5 h-5" /> Added to Cart</>
                                            ) : (
                                                <><ShoppingCart className="w-5 h-5" /> Add to Cart</>
                                            )}
                                        </motion.button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    )
}

export default function SearchResults({ result }) {
    const { setLastMetrics } = useStore()

    // Store metrics
    // Store metrics
    useEffect(() => {
        if (result?.metrics) {
            setLastMetrics(result.metrics)
        }
    }, [result, setLastMetrics])

    const path = result.path
    const metrics = result.metrics || {}

    return (
        <div className="space-y-6">
            {/* Success Banner */}
            <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between p-4 glass"
            >
                <div className="flex items-center gap-3">
                    <span className="text-green-400 text-lg">✅</span>
                    <span className="text-white/80">
                        Found results via <PathBadge path={path} /> path in{' '}
                        <span className="font-semibold text-primary-400">{Math.round(metrics.total_latency_ms)}ms</span>
                    </span>
                    {/* Show ACORN badge for filtered searches */}
                    {metrics.acorn_enabled && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">
                            <Filter className="w-3 h-3" />
                            ACORN
                        </span>
                    )}
                    {/* Show visual search badge */}
                    {metrics.visual_search && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-purple-500/20 text-purple-400 border border-purple-500/30">
                            <Eye className="w-3 h-3" />
                            Visual
                        </span>
                    )}
                </div>
                <span className="text-sm text-white/50">{metrics.route_reason}</span>
            </motion.div>

            {/* Results based on path */}
            {path === 'fast' && <FastPathResults results={result.results} />}
            {path === 'smart' && <SmartPathResults results={result.results} metrics={metrics} disambiguation={result.disambiguation} />}
            {path === 'visual' && <VisualPathResults results={result.results} metrics={metrics} />}
            {path === 'deep' && (
                // Deep path: Show bundle builder if bundle/curated_products available, otherwise fallback to grid
                (result.bundle || result.curated_products) ? (
                    <DeepPathResults
                        bundle={result.bundle}
                        curatedProducts={result.curated_products}
                        agentPaths={result.agent_paths}
                        explanations={result.explanations}
                        bundleExplanation={result.bundle_explanation}
                    />
                ) : (
                    // Timeout fallback: show results as smart path grid
                    <SmartPathResults results={result.results} metrics={metrics} />
                )
            )}
        </div>
    )
}

function PathBadge({ path }) {
    const styles = {
        fast: 'badge-fast',
        smart: 'badge-smart',
        deep: 'badge-deep',
        visual: 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
    }

    const icons = {
        fast: <Zap className="w-3 h-3" />,
        smart: <Brain className="w-3 h-3" />,
        deep: <Target className="w-3 h-3" />,
        visual: <Eye className="w-3 h-3" />
    }

    return (
        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${styles[path] || styles.smart}`}>
            {icons[path] || icons.smart}
            {path.toUpperCase()}
        </span>
    )
}

function FastPathResults({ results = [] }) {
    return (
        <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                <Zap className="w-5 h-5 text-green-400" />
                Quick Results
            </h2>
            <ProductGrid products={results} />
        </div>
    )
}

function SmartPathResults({ results = [], metrics = {}, disambiguation = null }) {
    // Separate primary and related matches
    const primaryResults = results.filter(p => p.match_tier === 'primary')
    const relatedResults = results.filter(p => p.match_tier !== 'primary')
    
    return (
        <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                <Brain className="w-5 h-5 text-blue-400" />
                Smart Recommendations
                {metrics.scoring_enabled && (
                    <span className="text-xs font-normal text-white/50 ml-2">
                        • AI-scored for your profile
                    </span>
                )}
            </h2>
            
            {/* Match Quality Summary */}
            {metrics.primary_matches !== undefined && (
                <div className="flex items-center gap-4 mb-4 text-sm">
                    <span className="flex items-center gap-1.5 text-emerald-400">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                        {metrics.primary_matches} exact matches
                    </span>
                    {results.length - metrics.primary_matches > 0 && (
                        <span className="flex items-center gap-1.5 text-white/50">
                            <span className="w-2 h-2 rounded-full bg-white/30"></span>
                            {results.length - metrics.primary_matches} related
                        </span>
                    )}
                    <span className="text-white/40 ml-auto">
                        {metrics.latency_ms?.toFixed(0) || '-'}ms
                    </span>
                </div>
            )}
            
            {/* Disambiguation info */}
            {disambiguation?.applied && (
                <div className="flex items-center gap-2 mb-4 text-sm text-white/60">
                    <Filter className="w-4 h-4 text-amber-400" />
                    <span>
                        Focused on <span className="text-amber-400 font-medium">{disambiguation.target_category?.replace(/_/g, ' ')}</span>
                        {disambiguation.excluded_categories?.length > 0 && (
                            <span className="text-white/40">
                                {' '}(excluded: {disambiguation.excluded_categories.join(', ').replace(/_/g, ' ')})
                            </span>
                        )}
                    </span>
                </div>
            )}
            
            {/* Primary Matches Section */}
            {primaryResults.length > 0 && (
                <div className="mb-6">
                    <h3 className="flex items-center gap-2 text-sm font-medium text-emerald-400 mb-3">
                        <Sparkles className="w-4 h-4" />
                        Best Matches
                    </h3>
                    <ProductGrid products={primaryResults} showScoring={true} tier="primary" />
                </div>
            )}
            
            {/* Related Matches Section */}
            {relatedResults.length > 0 && (
                <div>
                    {primaryResults.length > 0 && (
                        <h3 className="flex items-center gap-2 text-sm font-medium text-white/50 mb-3 mt-6">
                            <Package className="w-4 h-4" />
                            Related Products
                        </h3>
                    )}
                    <ProductGrid products={relatedResults} showScoring={true} tier="related" />
                </div>
            )}
            
            {/* Fallback if no tier separation */}
            {primaryResults.length === 0 && relatedResults.length === 0 && (
                <ProductGrid products={results} showScoring={true} />
            )}
        </div>
    )
}

function VisualPathResults({ results = [], metrics = {} }) {
    return (
        <div>
            <h2 className="flex items-center gap-2 text-xl font-semibold mb-4">
                <Eye className="w-5 h-5 text-purple-400" />
                Visual Search Results
                {metrics.text_combined && (
                    <span className="text-xs font-normal text-white/50 ml-2">
                        • Combined with text query
                    </span>
                )}
            </h2>
            <p className="text-white/60 text-sm mb-4">
                Found {metrics.candidates_searched || results.length} similar products based on your image
            </p>
            <ProductGrid products={results} showScoring={true} />
        </div>
    )
}

function DeepPathResults({ bundle, curatedProducts, agentPaths, explanations, bundleExplanation }) {
    const bundleItems = bundle?.bundle || []
    const { addToCart, cart } = useStore()
    const [addedItems, setAddedItems] = useState(new Set())
    const [selectedItems, setSelectedItems] = useState({}) // category -> selected item id
    const [modalProduct, setModalProduct] = useState(null) // Product for info modal
    const [isModalOpen, setIsModalOpen] = useState(false)
    
    // If curatedProducts is not available, derive from bundle items by grouping by category
    // Each bundle item becomes the only (and recommended) option in its category
    const effectiveCuratedProducts = curatedProducts || (() => {
        if (!bundleItems.length) return {}
        const grouped = {}
        bundleItems.forEach(item => {
            const cat = item.category || 'other'
            if (!grouped[cat]) grouped[cat] = []
            grouped[cat].push({ ...item, is_recommended: true })
        })
        return grouped
    })()
    
    // Get categories from effective curatedProducts
    const categories = Object.keys(effectiveCuratedProducts)
    
    // Initialize selected items with AI recommendations
    useEffect(() => {
        if (effectiveCuratedProducts && Object.keys(effectiveCuratedProducts).length > 0) {
            const initial = {}
            Object.entries(effectiveCuratedProducts).forEach(([cat, products]) => {
                const recommended = products.find(p => p.is_recommended)
                if (recommended) {
                    initial[cat] = recommended.id
                } else if (products.length > 0) {
                    initial[cat] = products[0].id
                }
            })
            setSelectedItems(initial)
        }
    }, [effectiveCuratedProducts])
    
    // Get currently selected products
    const getSelectedProducts = () => {
        if (!effectiveCuratedProducts || Object.keys(effectiveCuratedProducts).length === 0) return []
        return categories.map(cat => {
            const products = effectiveCuratedProducts[cat] || []
            const selectedId = selectedItems[cat]
            return products.find(p => p.id === selectedId) || products[0]
        }).filter(Boolean)
    }
    
    const selectedProducts = getSelectedProducts()
    const totalPrice = selectedProducts.reduce((sum, p) => sum + (p?.price || 0), 0)
    const totalProducts = categories.reduce((sum, cat) => sum + (effectiveCuratedProducts?.[cat]?.length || 0), 0)
    
    // Dynamic category styling - supports many product types
    const categoryStyles = {
        // Computing & Peripherals
        monitor: { icon: '🖥️', bg: 'bg-blue-500/10', border: 'border-blue-500/30', accent: 'text-blue-400' },
        keyboard: { icon: '⌨️', bg: 'bg-amber-500/10', border: 'border-amber-500/30', accent: 'text-amber-400' },
        mouse: { icon: '🖱️', bg: 'bg-green-500/10', border: 'border-green-500/30', accent: 'text-green-400' },
        laptop: { icon: '💻', bg: 'bg-violet-500/10', border: 'border-violet-500/30', accent: 'text-violet-400' },
        tablet: { icon: '📱', bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', accent: 'text-indigo-400' },
        phone: { icon: '📱', bg: 'bg-sky-500/10', border: 'border-sky-500/30', accent: 'text-sky-400' },
        printer: { icon: '🖨️', bg: 'bg-slate-500/10', border: 'border-slate-500/30', accent: 'text-slate-400' },
        router: { icon: '📶', bg: 'bg-teal-500/10', border: 'border-teal-500/30', accent: 'text-teal-400' },
        
        // Audio & Video
        headphones: { icon: '🎧', bg: 'bg-purple-500/10', border: 'border-purple-500/30', accent: 'text-purple-400' },
        speaker: { icon: '🔊', bg: 'bg-orange-500/10', border: 'border-orange-500/30', accent: 'text-orange-400' },
        microphone: { icon: '🎤', bg: 'bg-red-500/10', border: 'border-red-500/30', accent: 'text-red-400' },
        webcam: { icon: '📷', bg: 'bg-rose-500/10', border: 'border-rose-500/30', accent: 'text-rose-400' },
        camera: { icon: '📸', bg: 'bg-pink-500/10', border: 'border-pink-500/30', accent: 'text-pink-400' },
        tv: { icon: '📺', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', accent: 'text-cyan-400' },
        
        // Accessories & Storage
        lighting: { icon: '💡', bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', accent: 'text-yellow-400' },
        tripod: { icon: '📐', bg: 'bg-stone-500/10', border: 'border-stone-500/30', accent: 'text-stone-400' },
        lens: { icon: '🔍', bg: 'bg-fuchsia-500/10', border: 'border-fuchsia-500/30', accent: 'text-fuchsia-400' },
        'power bank': { icon: '🔋', bg: 'bg-lime-500/10', border: 'border-lime-500/30', accent: 'text-lime-400' },
        'memory card': { icon: '💾', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', accent: 'text-emerald-400' },
        
        // Fallback
        default: { icon: '📦', bg: 'bg-gray-500/10', border: 'border-gray-500/30', accent: 'text-gray-400' }
    }
    
    // Dynamic color palette for unknown categories
    const dynamicColors = [
        { bg: 'bg-blue-500/10', border: 'border-blue-500/30', accent: 'text-blue-400' },
        { bg: 'bg-purple-500/10', border: 'border-purple-500/30', accent: 'text-purple-400' },
        { bg: 'bg-green-500/10', border: 'border-green-500/30', accent: 'text-green-400' },
        { bg: 'bg-amber-500/10', border: 'border-amber-500/30', accent: 'text-amber-400' },
        { bg: 'bg-rose-500/10', border: 'border-rose-500/30', accent: 'text-rose-400' },
        { bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', accent: 'text-cyan-400' },
        { bg: 'bg-indigo-500/10', border: 'border-indigo-500/30', accent: 'text-indigo-400' },
        { bg: 'bg-orange-500/10', border: 'border-orange-500/30', accent: 'text-orange-400' },
    ]
    
    const getStyle = (cat, index = 0) => {
        const key = cat?.toLowerCase()
        if (categoryStyles[key]) return categoryStyles[key]
        // For unknown categories, use dynamic color based on index
        const color = dynamicColors[index % dynamicColors.length]
        return { icon: '📦', ...color }
    }
    
    const handleSelect = (category, productId) => {
        setSelectedItems(prev => ({ ...prev, [category]: productId }))
    }
    
    const handleAddToCart = (item) => {
        addToCart({ product_id: item.id, ...item })
        setAddedItems(prev => new Set([...prev, item.id]))
    }
    
    const handleAddAllSelected = () => {
        selectedProducts.forEach(item => {
            if (item) addToCart({ product_id: item.id, ...item })
        })
        setAddedItems(new Set(selectedProducts.map(p => p?.id).filter(Boolean)))
    }
    
    // Open product info modal
    const handleProductClick = (product) => {
        setModalProduct(product)
        setIsModalOpen(true)
    }
    
    // Get explanation for a product
    const getExplanation = (productId) => {
        return explanations?.find(e => e.product_id === productId)?.explanation
    }
    
    const isInCart = (itemId) => cart.some(c => c.product_id === itemId) || addedItems.has(itemId)
    const budgetUsed = bundle?.budget_used || 0

    return (
        <div className="space-y-6">
            {/* Product Info Modal */}
            <ProductInfoModal
                product={modalProduct}
                explanation={modalProduct ? getExplanation(modalProduct.id) : null}
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onAddToCart={handleAddToCart}
                isInCart={modalProduct ? isInCart(modalProduct.id) : false}
            />
            
            {/* Bundle Summary Header */}
            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-violet-600/20 via-purple-600/10 to-cyan-600/20 border border-white/10 p-6"
            >
                <div className="absolute top-0 right-0 w-64 h-64 bg-gradient-to-br from-violet-500/20 to-transparent rounded-full blur-3xl" />
                
                <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-3 mb-2">
                            <div className="p-2 bg-gradient-to-br from-violet-500 to-purple-600 rounded-xl">
                                <Layers className="w-5 h-5 text-white" />
                            </div>
                            <h2 className="text-xl md:text-2xl font-bold text-white">Build Your Bundle</h2>
                            <span className="text-xs bg-white/10 px-2 py-1 rounded-full text-white/60">
                                {categories.length} categories • {totalProducts} products
                            </span>
                        </div>
                        <p className="text-white/60 text-sm">Pick your favorites from each category • AI recommendations highlighted with ✨</p>
                    </div>
                    
                    <div className="flex items-center gap-6">
                        <div className="text-center">
                            <div className={`text-2xl font-bold ${budgetUsed > 1 ? 'text-red-400' : 'text-green-400'}`}>
                                ${totalPrice.toFixed(0)}
                            </div>
                            <p className="text-xs text-white/50">Your Selection</p>
                        </div>
                        
                        <motion.button
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={handleAddAllSelected}
                            className="px-6 py-3 bg-gradient-to-r from-violet-500 to-purple-600 rounded-xl 
                                     font-semibold text-white shadow-lg shadow-violet-500/30 flex items-center gap-2"
                        >
                            <ShoppingCart className="w-4 h-4" />
                            Add Bundle
                        </motion.button>
                    </div>
                </div>
            </motion.div>

            {/* Category Sections with Product Cards */}
            <div className="space-y-8">
                {categories.map((category, catIndex) => {
                    const style = getStyle(category, catIndex)
                    const products = effectiveCuratedProducts[category] || []
                    const selectedId = selectedItems[category]
                    
                    if (products.length === 0) return null
                    
                    return (
                        <motion.div
                            key={category}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: catIndex * 0.08 }}
                            className="bg-white/[0.02] rounded-2xl p-4 md:p-6 border border-white/5"
                        >
                            {/* Category Header */}
                            <div className="flex items-center gap-3 mb-5">
                                <div className={`w-10 h-10 rounded-xl ${style.bg} ${style.border} border flex items-center justify-center`}>
                                    <span className="text-xl">{style.icon}</span>
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-white capitalize">{category.replace(/_/g, ' ')}</h3>
                                    <span className="text-xs text-white/40">{products.length} curated options</span>
                                </div>
                            </div>
                            
                            {/* Product Cards Grid - responsive for more products */}
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-3">
                                {products.map((product, i) => {
                                    const isSelected = selectedId === product.id
                                    const isRecommended = product.is_recommended
                                    const productExplanation = explanations?.find(e => e.product_id === product.id)?.explanation
                                    
                                    return (
                                        <motion.div
                                            key={product.id || i}
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            transition={{ delay: i * 0.03 }}
                                            onClick={() => handleSelect(category, product.id)}
                                            className={`group relative cursor-pointer rounded-2xl border-2 transition-all duration-200
                                                ${isSelected 
                                                    ? 'border-violet-500 bg-violet-500/10 ring-2 ring-violet-500/30' 
                                                    : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.04]'
                                                }`}
                                        >
                                            {/* AI Recommended Badge */}
                                            {isRecommended && (
                                                <div className="absolute -top-2 left-4 px-2 py-0.5 bg-gradient-to-r from-violet-500 to-purple-600 
                                                              rounded-full text-[10px] font-bold text-white flex items-center gap-1 z-10 shadow-lg">
                                                    <Sparkles className="w-3 h-3" /> AI PICK
                                                </div>
                                            )}
                                            
                                            {/* Info Button - Opens Modal */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleProductClick(product)
                                                }}
                                                className="absolute top-2 right-2 w-7 h-7 bg-black/50 hover:bg-violet-500 
                                                         rounded-full flex items-center justify-center z-10 opacity-0 group-hover:opacity-100
                                                         transition-all duration-200 backdrop-blur-sm"
                                            >
                                                <Info className="w-4 h-4 text-white" />
                                            </button>
                                            
                                            {/* Selection Indicator */}
                                            {isSelected && (
                                                <div className="absolute top-2 left-2 w-6 h-6 bg-violet-500 rounded-full flex items-center justify-center z-10 shadow-lg">
                                                    <Check className="w-4 h-4 text-white" />
                                                </div>
                                            )}
                                            
                                            {/* Product Image */}
                                            <div className={`aspect-square rounded-t-xl overflow-hidden ${style.bg} relative`}>
                                                {product.image_url ? (
                                                    <img 
                                                        src={product.image_url} 
                                                        alt={product.name}
                                                        className="w-full h-full object-contain p-4 group-hover:scale-105 transition-transform duration-300"
                                                        onError={(e) => e.target.style.display = 'none'}
                                                    />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center text-4xl opacity-60">
                                                        {style.icon}
                                                    </div>
                                                )}
                                            </div>
                                            
                                            {/* Product Info */}
                                            <div className="p-4">
                                                {product.brand && (
                                                    <p className="text-[10px] font-medium text-white/40 uppercase tracking-wide mb-1">
                                                        {product.brand}
                                                    </p>
                                                )}
                                                <h4 className="font-medium text-white text-sm line-clamp-2 min-h-[2.5rem]">
                                                    {product.name}
                                                </h4>
                                                
                                                <div className="flex items-center justify-between mt-3">
                                                    <span className="text-lg font-bold text-white">${product.price?.toFixed(0)}</span>
                                                    {product.rating > 0 && (
                                                        <div className="flex items-center gap-1 text-xs text-white/60">
                                                            <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                                                            {product.rating?.toFixed(1)}
                                                        </div>
                                                    )}
                                                </div>
                                                
                                                {/* AI Explanation for recommended/selected products */}
                                                {(isRecommended || isSelected) && productExplanation && (
                                                    <motion.div 
                                                        initial={{ opacity: 0, height: 0 }}
                                                        animate={{ opacity: 1, height: 'auto' }}
                                                        className="mt-2 text-[11px] text-violet-300/80 bg-gradient-to-r from-violet-500/10 to-purple-500/10 
                                                                 p-2 rounded-lg border border-violet-500/20"
                                                    >
                                                        <div className="flex items-start gap-1">
                                                            <Brain className="w-3 h-3 text-violet-400 shrink-0 mt-0.5" />
                                                            <span className="line-clamp-2">{productExplanation}</span>
                                                        </div>
                                                    </motion.div>
                                                )}
                                                
                                                {/* Click for more info hint */}
                                                {isSelected && !productExplanation && (
                                                    <p className="mt-2 text-[10px] text-white/40 text-center">
                                                        Click ℹ️ for details
                                                    </p>
                                                )}
                                                
                                                {/* Quick Add Button */}
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        // Dispatch animation event
                                                        const rect = e.currentTarget.getBoundingClientRect()
                                                        window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
                                                            detail: {
                                                                x: rect.left + rect.width / 2,
                                                                y: rect.top + rect.height / 2,
                                                                productImage: product.image_url || product.image,
                                                                productName: product.name,
                                                                productPrice: product.price
                                                            }
                                                        }))
                                                        handleAddToCart(product)
                                                    }}
                                                    disabled={isInCart(product.id)}
                                                    className={`mt-3 w-full py-2 rounded-lg text-xs font-medium transition-all flex items-center justify-center gap-1
                                                        ${isInCart(product.id)
                                                            ? 'bg-green-500/20 text-green-400'
                                                            : 'bg-white/10 hover:bg-violet-500 text-white'
                                                        }`}
                                                >
                                                    {isInCart(product.id) ? <><Check className="w-3 h-3" /> Added</> : <><Plus className="w-3 h-3" /> Add</>}
                                                </button>
                                            </div>
                                        </motion.div>
                                    )
                                })}
                            </div>
                        </motion.div>
                    )
                })}
            </div>

            {/* Agent Paths */}
            {agentPaths?.status === 'paths_found' && agentPaths.paths?.length > 0 && (
                <AgentPathsSection paths={agentPaths.paths} gap={agentPaths.gap} />
            )}
        </div>
    )
}

// Beautiful Product Card for Bundle Items
function BundleProductCard({ item, explanation, onAdd, isAdded, isRecommended, index, categoryColor }) {
    const [imageError, setImageError] = useState(false)
    
    // Generate a placeholder gradient based on product name
    const getPlaceholderGradient = () => {
        const gradients = [
            'from-violet-600 to-purple-700',
            'from-blue-600 to-cyan-700',
            'from-emerald-600 to-teal-700',
            'from-amber-600 to-orange-700',
            'from-rose-600 to-pink-700',
            'from-indigo-600 to-blue-700'
        ]
        const hash = item.name?.split('').reduce((a, b) => a + b.charCodeAt(0), 0) || 0
        return gradients[hash % gradients.length]
    }
    
    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: index * 0.05 }}
            className={`group relative bg-white/[0.03] hover:bg-white/[0.06] border 
                     ${isRecommended ? 'border-violet-500/50 ring-2 ring-violet-500/20' : 'border-white/10 hover:border-white/20'} 
                     rounded-2xl overflow-hidden transition-all duration-300`}
        >
            {/* AI Recommended Badge */}
            {isRecommended && (
                <div className="absolute top-0 left-0 right-0 z-20 bg-gradient-to-r from-violet-500 to-purple-600 
                              py-1.5 px-3 flex items-center justify-center gap-2">
                    <Sparkles className="w-3.5 h-3.5 text-white" />
                    <span className="text-xs font-semibold text-white">AI TOP PICK</span>
                </div>
            )}
            
            {/* Product Image */}
            <div className={`relative aspect-square overflow-hidden bg-gradient-to-br from-white/5 to-white/[0.02] ${isRecommended ? 'mt-7' : ''}`}>
                {item.image_url && !imageError ? (
                    <img
                        src={item.image_url}
                        alt={item.name}
                        className="w-full h-full object-contain p-4 group-hover:scale-110 transition-transform duration-500"
                        onError={() => setImageError(true)}
                    />
                ) : (
                    <div className={`w-full h-full bg-gradient-to-br ${getPlaceholderGradient()} flex items-center justify-center`}>
                        <span className="text-5xl opacity-80">
                            {item.category === 'monitor' && '🖥️'}
                            {item.category === 'keyboard' && '⌨️'}
                            {item.category === 'mouse' && '🖱️'}
                            {item.category === 'headphones' && '🎧'}
                            {item.category === 'laptop' && '💻'}
                            {item.category === 'webcam' && '📷'}
                            {!['monitor', 'keyboard', 'mouse', 'headphones', 'laptop', 'webcam'].includes(item.category) && '📦'}
                        </span>
                    </div>
                )}
                
                {/* Rating Badge */}
                {item.rating > 0 && (
                    <div className="absolute top-3 left-3 flex items-center gap-1 px-2 py-1 
                                  bg-black/60 backdrop-blur-sm rounded-full text-xs font-medium">
                        <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                        <span className="text-white">{item.rating?.toFixed(1)}</span>
                    </div>
                )}
                
                {/* Utility Score Badge */}
                {item.utility > 0 && (
                    <div className="absolute top-3 right-3 px-2 py-1 bg-violet-500/80 backdrop-blur-sm 
                                  rounded-full text-xs font-medium text-white">
                        {Math.round(item.utility * 100)}% match
                    </div>
                )}
            </div>
            
            {/* Product Info */}
            <div className="p-4">
                {/* Brand */}
                {item.brand && (
                    <p className="text-xs font-medium text-white/40 uppercase tracking-wide mb-1">
                        {item.brand}
                    </p>
                )}
                
                {/* Name */}
                <h4 className="font-semibold text-white text-sm leading-tight line-clamp-2 min-h-[2.5rem]">
                    {item.name}
                </h4>
                
                {/* Price */}
                <div className="flex items-center justify-between mt-3">
                    <div className="flex items-baseline gap-1">
                        <span className="text-xl font-bold text-white">${item.price?.toFixed(0)}</span>
                        <span className="text-xs text-white/40">.{((item.price % 1) * 100).toFixed(0).padStart(2, '0')}</span>
                    </div>
                </div>
                
                {/* Explanation */}
                {explanation && (
                    <p className="mt-3 text-xs text-violet-300/80 bg-violet-500/10 p-2 rounded-lg line-clamp-2">
                        💡 {explanation}
                    </p>
                )}
                
                {/* Add Button */}
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={(e) => {
                        if (!isAdded) {
                            // Get button position for animation with product details
                            const rect = e.currentTarget.getBoundingClientRect()
                            window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
                                detail: {
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    productImage: item.image_url || item.image,
                                    productName: item.name,
                                    productPrice: item.price
                                }
                            }))
                        }
                        onAdd()
                    }}
                    disabled={isAdded}
                    className={`mt-4 w-full py-2.5 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2
                              ${isAdded 
                                ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                                : 'bg-white/10 hover:bg-white/20 text-white border border-white/10 hover:border-white/20'
                              }`}
                >
                    {isAdded ? (
                        <>
                            <Check className="w-4 h-4" />
                            Added to Cart
                        </>
                    ) : (
                        <>
                            <Plus className="w-4 h-4" />
                            Add to Cart
                        </>
                    )}
                </motion.button>
            </div>
        </motion.div>
    )
}

function ProductGrid({ products = [], showScoring = false, tier = null }) {
    const { addToCart, cart } = useStore()
    const [modalProduct, setModalProduct] = useState(null)
    const [isModalOpen, setIsModalOpen] = useState(false)
    const [addedItems, setAddedItems] = useState(new Set())

    const handleAddToCart = (product) => {
        addToCart({ product_id: product.product_id || product.id, ...product })
        setAddedItems(prev => new Set([...prev, product.product_id || product.id]))
    }
    
    const isInCart = (productId) => cart.some(c => c.product_id === productId) || addedItems.has(productId)

    if (products.length === 0) {
        return (
            <div className="text-center py-8 text-white/50">
                No products found. Try adjusting your search or budget.
            </div>
        )
    }

    // Tier-specific styling
    const tierStyles = {
        primary: 'border-emerald-500/30 hover:border-emerald-500/50',
        related: 'border-white/5 hover:border-white/10 opacity-90'
    }
    const cardClass = tier ? tierStyles[tier] : 'border-white/10 hover:border-primary-500/30'

    return (
        <>
            {/* Product Info Modal */}
            <ProductInfoModal
                product={modalProduct}
                explanation={null}
                isOpen={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onAddToCart={handleAddToCart}
                isInCart={modalProduct ? isInCart(modalProduct.product_id || modalProduct.id) : false}
            />
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {products.slice(0, 20).map((product, i) => {
                    const productId = product.product_id || product.id
                    
                    return (
                        <motion.div
                            key={productId || i}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.03 }}
                            className={`group glass p-4 card-hover relative border ${cardClass} cursor-pointer`}
                            onClick={() => {
                                setModalProduct(product)
                                setIsModalOpen(true)
                            }}
                        >
                            {/* Match Tier Badge */}
                            {product.match_tier === 'primary' && (
                                <div className="absolute top-2 left-2 z-10">
                                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 text-xs font-medium rounded-full border border-emerald-500/30">
                                        Best Match
                                    </span>
                                </div>
                            )}
                            
                            {/* Info Button */}
                            <button
                                onClick={(e) => {
                                    e.stopPropagation()
                                    setModalProduct(product)
                                    setIsModalOpen(true)
                                }}
                                className="absolute top-2 right-2 w-7 h-7 bg-black/50 hover:bg-violet-500 
                                         rounded-full flex items-center justify-center z-10 opacity-0 group-hover:opacity-100
                                         transition-all duration-200 backdrop-blur-sm"
                            >
                                <Info className="w-4 h-4 text-white" />
                            </button>
                            
                            {/* Product Image if available */}
                            <div className="w-full h-36 mb-3 rounded-lg overflow-hidden bg-white/5 flex items-center justify-center">
                                {product.image_url ? (
                                    <img 
                                        src={product.image_url} 
                                        alt={product.name}
                                        className="w-full h-full object-contain p-2 group-hover:scale-105 transition-transform"
                                        onError={(e) => e.target.style.display = 'none'}
                                    />
                                ) : (
                                    <Package className="w-12 h-12 text-white/20" />
                                )}
                            </div>
                            
                            {/* Brand */}
                            {product.brand && (
                                <p className="text-[10px] font-medium text-violet-400 uppercase tracking-wider mb-1">
                                    {product.brand}
                                </p>
                            )}
                            
                            <h3 className="font-semibold text-white text-sm line-clamp-2 min-h-[2.5rem]">{product.name}</h3>
                            
                            <p className="text-xs text-white/50 mt-1">
                                {product.category?.replace(/_/g, ' ')}
                            </p>

                            <div className="flex items-center justify-between mt-3">
                                <div>
                                    <span className="text-lg font-bold text-white">${product.price?.toFixed(2)}</span>
                                    <div className="flex items-center gap-2 text-xs mt-1">
                                        {product.rating > 0 && (
                                            <span className="flex items-center gap-1 text-white/60">
                                                <Star className="w-3 h-3 text-amber-400 fill-amber-400" />
                                                {product.rating?.toFixed(1)}
                                            </span>
                                        )}
                                        {/* Show AI score */}
                                        {(showScoring || product.score > 0) && (
                                            <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px]">
                                                {((product.score || product.utility || 0) * 100).toFixed(0)}% match
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <button
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        // Dispatch animation event
                                        const rect = e.currentTarget.getBoundingClientRect()
                                        window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
                                            detail: {
                                                x: rect.left + rect.width / 2,
                                                y: rect.top + rect.height / 2,
                                                productImage: product.image_url || product.image,
                                                productName: product.name,
                                                productPrice: product.price
                                            }
                                        }))
                                        handleAddToCart(product)
                                    }}
                                    disabled={isInCart(productId)}
                                    className={`px-3 py-2 rounded-lg text-xs font-medium transition-all flex items-center gap-1
                                        ${isInCart(productId)
                                            ? 'bg-green-500/20 text-green-400'
                                            : 'bg-violet-500 hover:bg-violet-600 text-white'
                                        }`}
                                >
                                    {isInCart(productId) ? <><Check className="w-3 h-3" /></> : <><Plus className="w-3 h-3" /> Add</>}
                                </button>
                            </div>
                        </motion.div>
                    )
                })}
            </div>
        </>
    )
}

function StatCard({ label, value, icon, highlight = false }) {
    return (
        <div className={`p-4 rounded-xl ${highlight ? 'bg-red-500/20 border border-red-500/30' : 'glass'}`}>
            <div className="flex items-center gap-2 text-white/50 text-sm mb-1">
                {icon}
                {label}
            </div>
            <p className="text-xl font-bold">{value}</p>
        </div>
    )
}

function BundleItem({ item, explanation }) {
    const { addToCart } = useStore()

    return (
        <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="glass p-4"
        >
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <h4 className="font-semibold">{item.name}</h4>
                    <p className="text-sm text-white/50">{item.category}</p>
                    {explanation && (
                        <p className="mt-2 text-sm text-primary-300 bg-primary-500/10 p-2 rounded-lg">
                            💡 {explanation}
                        </p>
                    )}
                </div>
                <div className="text-right">
                    <p className="text-lg font-bold text-primary-400">${item.price?.toFixed(2)}</p>
                    <p className="text-xs text-white/50">Utility: {item.utility?.toFixed(3)}</p>
                    <button
                        onClick={(e) => {
                            // Get button position for animation with product details
                            const rect = e.currentTarget.getBoundingClientRect()
                            window.dispatchEvent(new CustomEvent('add-to-cart-animation', {
                                detail: {
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    productImage: item.image_url || item.image,
                                    productName: item.name,
                                    productPrice: item.price
                                }
                            }))
                            addToCart({ product_id: item.id, ...item })
                        }}
                        className="mt-2 btn-secondary text-xs py-1"
                    >
                        Add to Cart
                    </button>
                </div>
            </div>
        </motion.div>
    )
}

function AgentPathsSection({ paths, gap }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-8 p-6 rounded-2xl bg-gradient-to-br from-purple-500/10 via-violet-500/5 to-pink-500/10 border border-purple-500/20"
        >
            <div className="flex items-center gap-3 mb-5">
                <div className="p-2.5 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl">
                    <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div>
                    <h3 className="text-lg font-semibold text-white">AI Budget Assistant</h3>
                    <p className="text-sm text-white/50">Smart alternatives to fit your budget</p>
                </div>
            </div>

            {gap > 0 && (
                <div className="flex items-center gap-3 p-4 mb-5 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                    <AlertCircle className="w-6 h-6 text-amber-400 flex-shrink-0" />
                    <div>
                        <p className="font-medium text-amber-200">Budget Exceeded</p>
                        <p className="text-sm text-amber-300/80">
                            You're <strong>${gap.toFixed(2)}</strong> over budget. Here are some options:
                        </p>
                    </div>
                </div>
            )}

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {paths.map((path, i) => {
                    const pathColors = {
                        downgrade: { bg: 'from-blue-500/20 to-cyan-500/20', border: 'border-blue-500/30', badge: 'bg-blue-500/30 text-blue-300' },
                        remove: { bg: 'from-orange-500/20 to-amber-500/20', border: 'border-orange-500/30', badge: 'bg-orange-500/30 text-orange-300' },
                        wait: { bg: 'from-green-500/20 to-emerald-500/20', border: 'border-green-500/30', badge: 'bg-green-500/30 text-green-300' },
                        default: { bg: 'from-purple-500/20 to-pink-500/20', border: 'border-purple-500/30', badge: 'bg-purple-500/30 text-purple-300' }
                    }
                    const colors = pathColors[path.path_type] || pathColors.default
                    
                    return (
                        <motion.div
                            key={i}
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: i * 0.1 }}
                            className={`p-4 rounded-xl bg-gradient-to-br ${colors.bg} border ${colors.border} hover:scale-[1.02] transition-transform`}
                        >
                            <div className="flex items-start justify-between mb-3">
                                <span className={`px-2.5 py-1 ${colors.badge} text-xs font-medium rounded-lg`}>
                                    {path.path_type?.replace('_', ' ').toUpperCase() || `Option ${i + 1}`}
                                </span>
                                {path.savings > 0 && (
                                    <span className="flex items-center gap-1 text-green-400 font-bold">
                                        <TrendingUp className="w-4 h-4" />
                                        -${path.savings.toFixed(0)}
                                    </span>
                                )}
                            </div>
                            
                            <p className="font-medium text-white text-sm mb-2">{path.summary}</p>
                            
                            <div className="space-y-1.5 text-xs">
                                <p className="text-white/70">
                                    <span className="text-white/40">Action:</span> {path.action}
                                </p>
                                <p className="text-white/50 italic">
                                    ⚖️ {path.trade_off}
                                </p>
                            </div>
                        </motion.div>
                    )
                })}
            </div>
        </motion.div>
    )
}
