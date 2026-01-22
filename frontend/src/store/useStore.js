import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useStore = create(
    persist(
        (set, get) => ({
            // User settings
            userId: 'demo_user',
            budget: 1000,

            // Cart
            cart: [],

            // Search history
            searchHistory: [],

            // Last result metrics
            lastMetrics: null,

            // Actions
            setUserId: (userId) => set({ userId }),

            setBudget: (budget) => set({ budget }),

            addToCart: (item) => set((state) => ({
                cart: [...state.cart, { ...item, quantity: 1, addedAt: Date.now() }]
            })),

            removeFromCart: (productId) => set((state) => ({
                cart: state.cart.filter(item => item.product_id !== productId)
            })),

            clearCart: () => set({ cart: [] }),

            getCartTotal: () => {
                const { cart } = get()
                return cart.reduce((sum, item) => sum + (item.price * (item.quantity || 1)), 0)
            },

            addToHistory: (entry) => set((state) => ({
                searchHistory: [entry, ...state.searchHistory.slice(0, 19)]
            })),

            setLastMetrics: (metrics) => set({ lastMetrics: metrics }),

            clearHistory: () => set({ searchHistory: [] }),
        }),
        {
            name: 'finbundle-storage',
            partialize: (state) => ({
                userId: state.userId,
                budget: state.budget,
                cart: state.cart,
                searchHistory: state.searchHistory,
            }),
        }
    )
)
