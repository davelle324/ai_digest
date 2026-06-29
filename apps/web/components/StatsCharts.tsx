'use client'

import type { Stats } from '@/lib/api'
import {
  Bar, BarChart, Cell, Legend, Line, LineChart, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const CATEGORY_COLORS: Record<string, string> = {
  top_stories: '#6366f1',
  research: '#8b5cf6',
  open_source: '#06b6d4',
  company: '#f59e0b',
  community: '#10b981',
}

const FALLBACK_COLORS = ['#6366f1', '#8b5cf6', '#06b6d4', '#f59e0b', '#10b981']

interface Props {
  stats: Stats
}

export default function StatsCharts({ stats }: Props) {
  return (
    <div className="space-y-8">
      {/* Stat cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Total Articles', value: stats.total_articles.toLocaleString() },
          { label: 'Active Sources', value: stats.total_sources.toLocaleString() },
          { label: 'Subscribers', value: stats.total_subscribers.toLocaleString() },
        ].map((card) => (
          <div key={card.label} className="bg-gray-800 rounded-lg border border-gray-700 p-5">
            <p className="text-sm text-gray-400">{card.label}</p>
            <p className="text-3xl font-bold text-white mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Articles per day */}
      <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4">
          Articles per day (last 30 days)
        </h2>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={stats.articles_per_day} margin={{ top: 4, right: 4, bottom: 0, left: -16 }}>
            <XAxis
              dataKey="date"
              tick={{ fill: '#9ca3af', fontSize: 11 }}
              tickFormatter={(d) => d.slice(5)}
              interval={4}
            />
            <YAxis tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
            <Tooltip
              contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
              labelStyle={{ color: '#e5e7eb' }}
              itemStyle={{ color: '#a5b4fc' }}
            />
            <Line type="monotone" dataKey="count" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Bar + Pie side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Articles per source */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4">
            Articles by source
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={stats.articles_per_source}
              layout="vertical"
              margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
            >
              <XAxis type="number" tick={{ fill: '#9ca3af', fontSize: 11 }} allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="name"
                width={130}
                tick={{ fill: '#d1d5db', fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
                labelStyle={{ color: '#e5e7eb' }}
                itemStyle={{ color: '#a5b4fc' }}
              />
              <Bar dataKey="count" fill="#6366f1" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Articles per category */}
        <div className="bg-gray-800 rounded-lg border border-gray-700 p-5">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-gray-400 mb-4">
            Articles by category
          </h2>
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={stats.articles_per_category}
                dataKey="count"
                nameKey="label"
                cx="50%"
                cy="45%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={3}
              >
                {stats.articles_per_category.map((entry, i) => (
                  <Cell
                    key={entry.category}
                    fill={CATEGORY_COLORS[entry.category] ?? FALLBACK_COLORS[i % FALLBACK_COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: '#1f2937', border: '1px solid #374151', borderRadius: 6 }}
                labelStyle={{ color: '#e5e7eb' }}
                itemStyle={{ color: '#e5e7eb' }}
              />
              <Legend
                formatter={(value) => <span style={{ color: '#d1d5db', fontSize: 12 }}>{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
