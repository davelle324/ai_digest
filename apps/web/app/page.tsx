import Link from 'next/link'
import NavBar from '@/components/NavBar'
import ArticleCard from '@/components/ArticleCard'
import { getArticles, getCategories, getSources } from '@/lib/api'

interface HomePageProps {
  searchParams: { page?: string; source?: string; category?: string }
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const page = Math.max(1, parseInt(searchParams.page || '1', 10))
  const sourceId = searchParams.source ? parseInt(searchParams.source, 10) : undefined
  const category = searchParams.category

  let data, sources, categories
  try {
    ;[data, sources, categories] = await Promise.all([
      getArticles(page, 20, sourceId, category),
      getSources(),
      getCategories(),
    ])
  } catch {
    return (
      <div className="min-h-screen flex flex-col">
        <NavBar />
        <main className="flex-1 flex items-center justify-center">
          <p className="text-red-400 text-lg">Failed to load articles. Is the API running?</p>
        </main>
      </div>
    )
  }

  const { items, total, pages } = data

  // Group sources by category, preserving category order from the API
  const categoryMap = new Map(categories.map((c) => [c.key, c.label]))
  const grouped = new Map<string, typeof sources>()
  for (const cat of categories) grouped.set(cat.key, [])
  for (const s of sources) {
    const key = s.category ?? '__other'
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(s)
  }

  function pageHref(p: number) {
    const params = new URLSearchParams({ page: String(p) })
    if (sourceId !== undefined) params.set('source', String(sourceId))
    if (category) params.set('category', category)
    return `/?${params.toString()}`
  }

  const activeLabel = sourceId
    ? sources.find((s) => s.id === sourceId)?.name
    : category
    ? categoryMap.get(category)
    : null

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-white">Latest AI/ML News</h1>
          <p className="mt-1 text-gray-400">
            {total} articles{activeLabel ? ` · ${activeLabel}` : ''}
          </p>
        </div>

        {/* Category + source filter panel */}
        <div className="mb-8 space-y-2">
          {/* All */}
          <div className="flex items-center gap-2 flex-wrap">
            <Link
              href="/"
              className={`text-sm font-semibold w-40 shrink-0 ${
                !sourceId && !category ? 'text-white' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              All Sources
            </Link>
          </div>

          {/* One row per category */}
          {categories.map((cat) => {
            const catSources = grouped.get(cat.key) ?? []
            const isCatActive = category === cat.key && !sourceId
            return (
              <div key={cat.key} className="flex items-start gap-2 flex-wrap">
                <Link
                  href={`/?category=${cat.key}`}
                  className={`text-sm font-semibold w-40 shrink-0 pt-0.5 transition-colors ${
                    isCatActive
                      ? 'text-indigo-400'
                      : 'text-gray-400 hover:text-gray-200'
                  }`}
                >
                  {cat.label}
                </Link>
                <div className="flex flex-wrap gap-1.5">
                  {catSources.map((s) => {
                    const isActive = sourceId === s.id
                    return (
                      <Link
                        key={s.id}
                        href={`/?source=${s.id}`}
                        className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors ${
                          isActive
                            ? 'bg-indigo-600 text-white'
                            : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                        }`}
                      >
                        {s.name}
                      </Link>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>

        {items.length === 0 ? (
          <p className="text-gray-400 text-center py-20">
            No articles yet. Trigger a fetch via{' '}
            <code className="bg-gray-800 px-1 rounded">POST /admin/fetch</code>.
          </p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map((article) => (
              <ArticleCard key={article.id} article={article} />
            ))}
          </div>
        )}

        {pages > 1 && (
          <div className="mt-10 flex items-center justify-center gap-4">
            {page > 1 && (
              <Link
                href={pageHref(page - 1)}
                className="px-4 py-2 rounded-md bg-gray-800 text-white hover:bg-gray-700 transition-colors text-sm font-medium"
              >
                ← Previous
              </Link>
            )}
            <span className="text-gray-400 text-sm">
              Page {page} of {pages}
            </span>
            {page < pages && (
              <Link
                href={pageHref(page + 1)}
                className="px-4 py-2 rounded-md bg-gray-800 text-white hover:bg-gray-700 transition-colors text-sm font-medium"
              >
                Next →
              </Link>
            )}
          </div>
        )}
      </main>
    </div>
  )
}
