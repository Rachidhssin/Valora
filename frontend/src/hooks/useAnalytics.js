/**
 * useAnalytics - Hook for tracking success indicators
 * 
 * Tracks user interactions for CTR, cart rate, constraint compliance, and speed metrics.
 * 
 * Usage:
 * ```jsx
 * const { sessionId, trackImpression, trackClick, trackCartAdd, endSession } = useAnalytics();
 * 
 * // After search results load
 * useEffect(() => {
 *   if (results.length > 0) {
 *     trackImpression(results, budget, query, searchPath, latency);
 *   }
 * }, [results]);
 * 
 * // When user clicks a product
 * const handleProductClick = (product, index) => {
 *   trackClick(product.product_id, index, product.price, budget);
 *   // ... navigate to product
 * };
 * 
 * // When user adds to cart
 * const handleAddToCart = (product) => {
 *   trackCartAdd(product.product_id, product.price, budget, true);
 *   // ... add to cart logic
 * };
 * ```
 */

import { useCallback, useEffect, useRef, useState } from 'react';

const API_BASE = 'http://localhost:8123';

export function useAnalytics() {
    const [sessionId, setSessionId] = useState(null);
    const [isInitialized, setIsInitialized] = useState(false);
    const sessionRef = useRef(null);
    const budgetRef = useRef(1000);

    // Create session on mount
    useEffect(() => {
        const createSession = async () => {
            try {
                const response = await fetch(`${API_BASE}/api/analytics/session`, {
                    method: 'POST',
                });
                const data = await response.json();
                setSessionId(data.session_id);
                sessionRef.current = data.session_id;
                setIsInitialized(true);
                console.log('📊 Analytics session started:', data.session_id);
            } catch (error) {
                console.warn('Analytics session creation failed:', error);
                // Generate local session ID as fallback
                const localId = `local_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
                setSessionId(localId);
                sessionRef.current = localId;
                setIsInitialized(true);
            }
        };

        createSession();

        // End session on unmount/page leave
        return () => {
            if (sessionRef.current) {
                // Use sendBeacon for reliability on page leave
                const url = `${API_BASE}/api/analytics/session/${sessionRef.current}/end`;
                navigator.sendBeacon(url);
            }
        };
    }, []);

    /**
     * Track product impressions (when products are shown to user)
     */
    const trackImpression = useCallback(async (products, budget, query, path = 'smart', latencyMs = 0, userId = 'anonymous') => {
        if (!sessionRef.current) return;
        budgetRef.current = budget;

        try {
            const response = await fetch(`${API_BASE}/api/analytics/track/impression`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionRef.current,
                    products: products.map(p => ({
                        product_id: p.product_id || p.id || '',
                        price: p.price || 0
                    })),
                    budget,
                    query,
                    path,
                    latency_ms: latencyMs,
                    user_id: userId
                })
            });

            const result = await response.json();
            console.log(`📊 Tracked ${result.impressions_count} impressions (${result.compliance_rate}% within budget)`);
            return result;
        } catch (error) {
            console.warn('Failed to track impressions:', error);
            return null;
        }
    }, []);

    /**
     * Track product click
     */
    const trackClick = useCallback(async (productId, position, price, budget = null) => {
        if (!sessionRef.current) return;

        try {
            const response = await fetch(`${API_BASE}/api/analytics/track/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionRef.current,
                    product_id: productId,
                    position,
                    price,
                    budget: budget || budgetRef.current
                })
            });

            const result = await response.json();
            console.log(`📊 Tracked click: position ${position}, ${result.within_budget ? '✓ in budget' : '⚠ over budget'}`);
            return result;
        } catch (error) {
            console.warn('Failed to track click:', error);
            return null;
        }
    }, []);

    /**
     * Track add to cart
     */
    const trackCartAdd = useCallback(async (productId, price, budget = null, isRecommended = false) => {
        if (!sessionRef.current) return;

        try {
            const response = await fetch(`${API_BASE}/api/analytics/track/cart`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionRef.current,
                    product_id: productId,
                    price,
                    budget: budget || budgetRef.current,
                    is_recommended: isRecommended
                })
            });

            const result = await response.json();
            console.log(`📊 Tracked cart add: ${result.within_budget ? '✓ in budget' : '⚠ over budget'}`);
            return result;
        } catch (error) {
            console.warn('Failed to track cart add:', error);
            return null;
        }
    }, []);

    /**
     * End the current session
     */
    const endSession = useCallback(async () => {
        if (!sessionRef.current) return;

        try {
            await fetch(`${API_BASE}/api/analytics/session/${sessionRef.current}/end`, {
                method: 'POST'
            });
            console.log('📊 Analytics session ended');
        } catch (error) {
            console.warn('Failed to end session:', error);
        }
    }, []);

    return {
        sessionId,
        isInitialized,
        trackImpression,
        trackClick,
        trackCartAdd,
        endSession
    };
}

/**
 * Fetch analytics dashboard data
 */
export async function fetchDashboard(hours = 24) {
    try {
        const response = await fetch(`${API_BASE}/api/analytics/dashboard?hours=${hours}`);
        return await response.json();
    } catch (error) {
        console.error('Failed to fetch dashboard:', error);
        return null;
    }
}

/**
 * Fetch specific metric
 */
export async function fetchMetric(metric, hours = 24) {
    const endpoints = {
        ctr: 'ctr',
        'cart-rate': 'cart-rate',
        compliance: 'compliance',
        speed: 'speed'
    };

    const endpoint = endpoints[metric];
    if (!endpoint) {
        throw new Error(`Unknown metric: ${metric}`);
    }

    try {
        const response = await fetch(`${API_BASE}/api/analytics/${endpoint}?hours=${hours}`);
        return await response.json();
    } catch (error) {
        console.error(`Failed to fetch ${metric}:`, error);
        return null;
    }
}

export default useAnalytics;
