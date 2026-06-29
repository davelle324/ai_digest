import NavBar from '@/components/NavBar'
import StatsCharts from '@/components/StatsCharts'
import { getStats } from '@/lib/api'

export const metadata = { title: 'Stats — AI Digest' }

export default async function StatsPage() {
  let stats
  try {
    stats = await getStats()
  } catch {
    return (
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <main className="flex-1 flex items-center justify-center">
          <p className="text-red-400 text-lg">Failed to load stats. Is the API running?</p>
        </main>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Stats</h1>
          <p className="mt-1 text-gray-400">An overview of your digest pipeline</p>
        </div>
        <StatsCharts stats={stats} />
      </main>
    </div>
  )
}
