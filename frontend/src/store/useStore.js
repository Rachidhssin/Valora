import { create } from 'zustand'
import { persist } from 'zustand/middleware'

/**
 * FinBundle Global Store
 * 
 * State management for:
 * - User settings (budget, userId)
 * - Cart (bundle items)
 * - Search context (gift/urgent/exploring)
 * - Financial DNA profile
 * - Search history & metrics
 */
export const useStore = create(
    persist(
        (set, get) => ({
            // === User Settings ===
            userId: 'demo_user',
            budget: 1000,

            // === Search Context ===
            // 'gift' | 'urgent' | 'exploring' | null
            searchContext: null,

            // === Financial DNA ===
            // Inferred from browsing behavior (or defaults for demo)
            financialDNA: {
                archetype: 'value_hunter',
                confidence: 0.72,
                traits: {
                    deliberation: 0.65,
                    priceSensitivity: 0.85,
                    cashFlow: 0.55,
                    purchaseReadiness: 0.70
                }
            },

            // === Cart / Bundle ===
            cart: [],
            bundleQualityScore: 0,

            // === Search History ===
            searchHistory: [],
            lastMetrics: null,
            lastSearchResult: null,

            // === UI State ===
            isCounterfactualOpen: false,

            // === Actions ===

            // User settings
            setUserId: (userId) => set({ userId }),
            setBudget: (budget) => set({ budget }),
            setSearchContext: (searchContext) => set({ searchContext }),

            // Financial DNA
            setFinancialDNA: (dna) => set({ financialDNA: dna }),
            updateFinancialDNA: (updates) => set((state) => ({
                financialDNA: { ...state.financialDNA, ...updates }
            })),

            // Cart actions
            addToCart: (item) => set((state) => {
                // Don't add duplicates
                if (state.cart.some(i => i.product_id === item.product_id)) {
                    return state
                }
                return {
                    cart: [...state.cart, {
                        ...item,
                        quantity: 1,
                        addedAt: Date.now()
                    }]
                }
            }),

            removeFromCart: (productId) => set((state) => ({
                cart: state.cart.filter(item => item.product_id !== productId)
            })),

            updateQuantity: (productId, quantity) => set((state) => ({
                cart: state.cart.map(item =>
                    item.product_id === productId
                        ? { ...item, quantity: Math.max(1, quantity) }
                        : item
                )
            })),

            clearCart: () => set({ cart: [], bundleQualityScore: 0 }),

            setBundleQualityScore: (score) => set({ bundleQualityScore: score }),

            getCartTotal: () => {
                const { cart } = get()
                return cart.reduce((sum, item) => sum + (item.price * (item.quantity || 1)), 0)
            },

            // Search history
            addToHistory: (entry) => set((state) => ({
                searchHistory: [entry, ...state.searchHistory.slice(0, 19)]
            })),

            setLastMetrics: (metrics) => set({ lastMetrics: metrics }),
            setLastSearchResult: (result) => set({ lastSearchResult: result }),
            clearHistory: () => set({ searchHistory: [] }),

            // UI state
            setCounterfactualOpen: (isOpen) => set({ isCounterfactualOpen: isOpen }),

            // Demo reset - useful for presentations
            resetToDemo: () => set({
                userId: 'demo_user',
                budget: 1500,
                cart: [],
                searchContext: null,
                bundleQualityScore: 0,
                financialDNA: {
                    archetype: 'value_hunter',
                    confidence: 0.72,
                    traits: {
                        deliberation: 0.65,
                        priceSensitivity: 0.85,
                        cashFlow: 0.55,
                        purchaseReadiness: 0.70
                    }
                },
                searchHistory: [],
                lastMetrics: null,
                lastSearchResult: null
            }),
        }),
        {
            name: 'finbundle-storage',
            partialize: (state) => ({
                userId: state.userId,
                budget: state.budget,
                cart: state.cart,
                searchHistory: state.searchHistory,
                financialDNA: state.financialDNA,
                searchContext: state.searchContext,
            }),
        }
    )
)
