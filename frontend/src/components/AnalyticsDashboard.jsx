import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    BarChart, Bar, PieChart, Pie, Cell, AreaChart, Area
} from 'recharts';
import {
    Activity, ShoppingCart, DollarSign, Zap, TrendingUp,
    ArrowUpRight, ArrowDownRight, Clock, Target, AlertCircle
} from 'lucide-react';
import { fetchDashboard } from '../hooks/useAnalytics';

const COLORS = ['#8b5cf6', '#22d3ee', '#f472b6', '#a78bfa'];

export default function AnalyticsDashboard({ onClose }) {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [timeRange, setTimeRange] = useState(24); // Hours

    useEffect(() => {
        loadData();
    }, [timeRange]);

    const loadData = async () => {
        setLoading(true);
        const dashboardData = await fetchDashboard(timeRange);
        if (dashboardData) {
            setData(dashboardData);
        }
        setLoading(false);
    };

    if (loading) {
        return (
            <div className="min-h-screen bg-[#08080c] flex items-center justify-center text-white">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
                    <p className="text-white/50">Loading analytics...</p>
                </div>
            </div>
        );
    }

    if (!data) return null;

    const { engagement, constraint_compliance, speed_metrics, summary } = data;

    return (
        <div className="min-h-screen bg-[#08080c] text-white p-6 md:p-12">
            <div className="max-w-7xl mx-auto space-y-8">

                {/* Header */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                    <div>
                        <h1 className="text-3xl font-bold bg-gradient-to-r from-violet-400 to-cyan-400 bg-clip-text text-transparent">
                            Success Indicators
                        </h1>
                        <p className="text-white/50 mt-1">Real-time performance metrics</p>
                    </div>

                    <div className="flex items-center gap-3">
                        {[1, 6, 24, 168].map(h => (
                            <button
                                key={h}
                                onClick={() => setTimeRange(h)}
                                className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${timeRange === h
                                        ? 'bg-violet-500/20 text-violet-300 border border-violet-500/30'
                                        : 'bg-white/[0.03] text-white/40 hover:text-white border border-white/[0.06]'
                                    }`}
                            >
                                {h === 1 ? '1h' : h < 24 ? `${h}h` : `${h / 24}d`}
                            </button>
                        ))}
                        <button
                            onClick={onClose}
                            className="px-4 py-2 bg-white/[0.03] hover:bg-white/[0.06] rounded-xl border border-white/[0.06]"
                        >
                            Close
                        </button>
                    </div>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    <KPICard
                        title="Engagement Score"
                        value={summary.scores.engagement_score.toFixed(0)}
                        icon={<Activity />}
                        color="violet"
                        subtext="CTR & Cart Activity"
                    />
                    <KPICard
                        title="Conversion Score"
                        value={summary.scores.conversion_score.toFixed(0)}
                        icon={<ShoppingCart />}
                        color="cyan"
                        subtext="Sales performance"
                    />
                    <KPICard
                        title="Budget Compliance"
                        value={`${constraint_compliance.overall_compliance}%`}
                        icon={<Target />}
                        color="emerald"
                        subtext="Adherence to constraints"
                    />
                    <KPICard
                        title="Speed Score"
                        value={summary.scores.speed_score.toFixed(0)}
                        icon={<Zap />}
                        color="amber"
                        subtext="Latency & discovery time"
                    />
                </div>

                {/* Main Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

                    {/* Activity Chart */}
                    <div className="lg:col-span-2 p-6 bg-white/[0.02] border border-white/[0.06] rounded-2xl">
                        <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-violet-400" />
                            Engagement Overview
                        </h3>
                        <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={[
                                    { name: 'Impressions', value: engagement.ctr.impressions },
                                    { name: 'Clicks', value: engagement.ctr.clicks },
                                    { name: 'Cart Adds', value: engagement.cart_rate.total_cart_adds }
                                ]}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                                    <XAxis dataKey="name" stroke="#ffffff40" axisLine={false} tickLine={false} />
                                    <YAxis stroke="#ffffff40" axisLine={false} tickLine={false} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#0f0f13', borderColor: '#ffffff20', borderRadius: '12px' }}
                                        itemStyle={{ color: '#fff' }}
                                        cursor={{ fill: '#ffffff05' }}
                                    />
                                    <Bar dataKey="value" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                                        {
                                            [0, 1, 2].map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                            ))
                                        }
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-6">
                            <div className="text-center p-3 bg-white/[0.02] rounded-xl">
                                <p className="text-xs text-white/40">CTR</p>
                                <p className="text-xl font-bold text-violet-400">{engagement.ctr.ctr}%</p>
                            </div>
                            <div className="text-center p-3 bg-white/[0.02] rounded-xl">
                                <p className="text-xs text-white/40">Cart Rate</p>
                                <p className="text-xl font-bold text-cyan-400">{engagement.cart_rate.cart_rate}%</p>
                            </div>
                            <div className="text-center p-3 bg-white/[0.02] rounded-xl">
                                <p className="text-xs text-white/40">Conversion</p>
                                <p className="text-xl font-bold text-pink-400">{engagement.cart_rate.conversion_rate}%</p>
                            </div>
                        </div>
                    </div>

                    {/* Insights Panel */}
                    <div className="p-6 bg-gradient-to-br from-violet-900/10 to-transparent border border-white/[0.06] rounded-2xl">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <AlertCircle className="w-5 h-5 text-cyan-400" />
                            AI Insights
                        </h3>
                        <div className="space-y-4">
                            {summary.insights.map((insight, i) => (
                                <div key={i} className="p-4 bg-white/[0.03] rounded-xl border border-white/[0.05]">
                                    <p className="text-sm text-white/80 leading-relaxed">
                                        {insight}
                                    </p>
                                </div>
                            ))}
                            {summary.insights.length === 0 && (
                                <p className="text-white/40 text-sm">No critical insights at this time.</p>
                            )}
                        </div>

                        <div className="mt-8 pt-6 border-t border-white/[0.05]">
                            <h4 className="text-xs font-semibold text-white/30 uppercase tracking-wider mb-3">Overall Rating</h4>
                            <div className="flex items-center gap-3">
                                <span className="text-3xl">{summary.rating.split(' ')[0]}</span>
                                <span className="text-lg font-medium text-white/80">{summary.rating.split(' ').slice(1).join(' ')}</span>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Secondary Metrics */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                    {/* Speed Metrics */}
                    <div className="p-6 bg-white/[0.02] border border-white/[0.06] rounded-2xl">
                        <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                            <Clock className="w-5 h-5 text-amber-400" />
                            Speed Performance
                        </h3>
                        <div className="space-y-4">
                            <MetricRow
                                label="Search Latency"
                                value={`${speed_metrics.avg_search_latency_ms}ms`}
                                target="< 300ms"
                                status={speed_metrics.avg_search_latency_ms < 300 ? 'good' : 'warning'}
                            />
                            <MetricRow
                                label="Time to First Click"
                                value={`${(speed_metrics.avg_time_to_first_click_ms / 1000).toFixed(1)}s`}
                                target="< 5s"
                                status={speed_metrics.avg_time_to_first_click_ms < 5000 ? 'good' : 'neutral'}
                            />
                            <MetricRow
                                label="Time to Cart"
                                value={`${(speed_metrics.avg_time_to_cart_ms / 1000).toFixed(1)}s`}
                                target="< 30s"
                                status={speed_metrics.avg_time_to_cart_ms < 30000 ? 'good' : 'neutral'}
                            />
                        </div>
                    </div>

                    {/* Compliance Metrics */}
                    <div className="p-6 bg-white/[0.02] border border-white/[0.06] rounded-2xl">
                        <h3 className="text-lg font-semibold mb-6 flex items-center gap-2">
                            <DollarSign className="w-5 h-5 text-emerald-400" />
                            Budget Compliance
                        </h3>
                        <div className="space-y-4">
                            <MetricRow
                                label="Impressions within Budget"
                                value={`${constraint_compliance.impression_compliance}%`}
                                target="100%"
                                status={constraint_compliance.impression_compliance > 90 ? 'good' : 'warning'}
                            />
                            <MetricRow
                                label="Clicks within Budget"
                                value={`${constraint_compliance.click_compliance}%`}
                                target="100%"
                                status={constraint_compliance.click_compliance > 90 ? 'good' : 'warning'}
                            />
                            <MetricRow
                                label="Cart Adds within Budget"
                                value={`${constraint_compliance.cart_compliance}%`}
                                target="100%"
                                status={constraint_compliance.cart_compliance > 90 ? 'good' : 'warning'}
                            />
                            <div className="pt-4 mt-4 border-t border-white/[0.05]">
                                <div className="flex justify-between items-center">
                                    <span className="text-sm text-white/50">Over-Budget Recommendations</span>
                                    <span className="text-sm font-semibold text-red-400">
                                        {constraint_compliance.over_budget_rate}%
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}

function KPICard({ title, value, icon, color, subtext }) {
    const colors = {
        violet: 'text-violet-400 bg-violet-500/10 border-violet-500/20',
        cyan: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
        emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
        amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
    };

    return (
        <div className={`p-6 rounded-2xl border ${colors[color].split(' ').slice(1).join(' ')}`}>
            <div className="flex justify-between items-start mb-4">
                <div className={`p-2 rounded-lg ${colors[color].split(' ')[1]}`}>
                    {React.cloneElement(icon, { className: `w-5 h-5 ${colors[color].split(' ')[0]}` })}
                </div>
            </div>
            <h3 className="text-3xl font-bold mb-1">{value}</h3>
            <p className="text-sm font-medium opacity-80 mb-1">{title}</p>
            <p className="text-xs opacity-50">{subtext}</p>
        </div>
    );
}

function MetricRow({ label, value, target, status }) {
    const statusColors = {
        good: 'text-emerald-400',
        warning: 'text-amber-400',
        bad: 'text-red-400',
        neutral: 'text-white/60'
    };

    return (
        <div className="flex items-center justify-between p-3 bg-white/[0.02] rounded-xl hover:bg-white/[0.04] transition-colors">
            <span className="text-sm text-white/60">{label}</span>
            <div className="flex items-center gap-4">
                <span className="text-xs text-white/30">Target: {target}</span>
                <span className={`font-mono font-medium ${statusColors[status]}`}>{value}</span>
            </div>
        </div>
    );
}
