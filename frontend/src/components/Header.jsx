import { motion } from 'framer-motion'

export default function Header() {
    return (
        <header>
            <motion.h1
                className="text-5xl font-bold gradient-text"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                🛒 FinBundle
            </motion.h1>
            <motion.p
                className="mt-2 text-lg text-white/60"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.1 }}
            >
                AI-Powered Smart Product Discovery
            </motion.p>
        </header>
    )
}
