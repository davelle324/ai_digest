import Link from 'next/link'
import type { Article } from '@/lib/api'

interface ArticleCardProps {
  article: Article
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return ''
  try {
    return new Date(dateStr).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    })
  } catch {
    return ''
  }
}

function truncate(text: string | null, maxLength: number): string {
  if (!text) return ''
  if (text.length <= maxLength) return text
  return text.slice(0, maxLength).trimEnd() + '…'
}

export default function ArticleCard({ article }: ArticleCardProps) {
  const preview = truncate(article.summary || article.excerpt, 150)
  const displayDate = formatDate(article.published_at || article.fetched_at)

  return (
    <div className="bg-gray-800 rounded-lg p-5 flex flex-col gap-3 hover:bg-gray-750 transition-colors border border-gray-700">
      <div className="flex items-start justify-between gap-2">
        <Link
          href={`/article/${article.id}`}
          className="text-white font-semibold text-base leading-snug hover:text-indigo-400 transition-colors line-clamp-2"
        >
          {article.title}
        </Link>
      </div>

      <div className="flex items-center gap-3 text-xs">
        <span className="inline-block bg-indigo-900 text-indigo-300 px-2 py-0.5 rounded-full font-medium">
          {article.source.name}
        </span>
        {displayDate && (
          <span className="text-gray-400">{displayDate}</span>
        )}
      </div>

      {preview && (
        <p className="text-gray-300 text-sm leading-relaxed">{preview}</p>
      )}

      <div className="mt-auto">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-400 text-sm hover:text-indigo-300 transition-colors font-medium"
        >
          Read more →
        </a>
      </div>
    </div>
  )
}
