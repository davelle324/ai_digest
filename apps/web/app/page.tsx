import Link from 'next/link'
import NavBar from '@/components/NavBar'
import ArticleCard from '@/components/ArticleCard'
import { getArticles } from '@/lib/api'

interface HomePageProps {
  searchParams: { page?: string }
}

export default async function HomePage({ searchParams }: HomePageProps) {
  const page = Math.max(1, parseInt(searchParams.page || '1', 10))

  let data
  try {
    data = await getArticles(page, 20)
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

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white">Latest AI/ML News</h1>
          <p className="mt-1 text-gray-400">{total} articles from top sources</p>
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

        {/* Pagination */}
        {pages > 1 && (
          <div className="mt-10 flex items-center justify-center gap-4">
            {page > 1 && (
              <Link
                href={`/?page=${page - 1}`}
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
                href={`/?page=${page + 1}`}
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
