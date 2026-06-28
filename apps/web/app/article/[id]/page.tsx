import Link from 'next/link'
import NavBar from '@/components/NavBar'
import { getArticle } from '@/lib/api'
import { notFound } from 'next/navigation'

interface ArticlePageProps {
  params: { id: string }
}

function stripHtml(text: string | null): string {
  if (!text) return ''
  return text
    .replace(/<[^>]*>/g, ' ')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim()
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    })
  } catch {
    return ''
  }
}

export default async function ArticlePage({ params }: ArticlePageProps) {
  const id = parseInt(params.id, 10)
  if (isNaN(id)) notFound()

  let article
  try {
    article = await getArticle(id)
  } catch {
    notFound()
  }

  const displayDate = formatDate(article.published_at || article.fetched_at)
  const content = stripHtml(article.summary || article.excerpt)

  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 max-w-3xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-10">
        <Link
          href="/"
          className="inline-flex items-center text-indigo-400 hover:text-indigo-300 text-sm mb-8 transition-colors"
        >
          ← Back to all articles
        </Link>

        <article className="space-y-6">
          <header className="space-y-3">
            <div className="flex items-center gap-3 text-sm">
              <span className="inline-block bg-indigo-900 text-indigo-300 px-2 py-0.5 rounded-full font-medium">
                {article.source.name}
              </span>
              {displayDate && (
                <span className="text-gray-400">{displayDate}</span>
              )}
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white leading-tight">
              {article.title}
            </h1>
          </header>

          {content && (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-3">
                {article.summary ? 'AI Summary' : 'Excerpt'}
              </h2>
              <p className="text-gray-200 leading-relaxed">{content}</p>
            </div>
          )}

          <div className="pt-2">
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500
                         text-white font-semibold rounded-md transition-colors"
            >
              Read original article →
            </a>
          </div>
        </article>
      </main>
    </div>
  )
}
