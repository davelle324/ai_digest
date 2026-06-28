const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Source {
  id: number
  name: string
  source_type: string
  url: string
  category: string | null
  enabled: boolean
}

export interface Category {
  key: string
  label: string
}

export interface Article {
  id: number
  title: string
  url: string
  excerpt: string | null
  summary: string | null
  published_at: string | null
  fetched_at: string
  source: Source
}

export interface ArticleListResponse {
  items: Article[]
  total: number
  page: number
  pages: number
}

export async function getArticles(
  page = 1,
  limit = 20,
  sourceId?: number,
  category?: string
): Promise<ArticleListResponse> {
  const params = new URLSearchParams({ page: String(page), limit: String(limit) })
  if (sourceId !== undefined) params.set('source_id', String(sourceId))
  if (category !== undefined) params.set('category', category)
  const res = await fetch(`${API_URL}/articles?${params.toString()}`, {
    next: { revalidate: 60 },
  })
  if (!res.ok) throw new Error(`Failed to fetch articles: ${res.status}`)
  return res.json()
}

export async function getCategories(): Promise<Category[]> {
  const res = await fetch(`${API_URL}/sources/categories`, { next: { revalidate: 3600 } })
  if (!res.ok) throw new Error(`Failed to fetch categories: ${res.status}`)
  return res.json()
}

export async function getArticle(id: number): Promise<Article> {
  const res = await fetch(`${API_URL}/articles/${id}`, {
    next: { revalidate: 60 },
  })
  if (!res.ok) throw new Error(`Failed to fetch article ${id}: ${res.status}`)
  return res.json()
}

export async function getSources(): Promise<Source[]> {
  const res = await fetch(`${API_URL}/sources`, { next: { revalidate: 300 } })
  if (!res.ok) throw new Error(`Failed to fetch sources: ${res.status}`)
  return res.json()
}

export async function subscribe(
  email: string,
  cadence: 'daily' | 'weekly'
): Promise<{ message: string }> {
  const res = await fetch(`${API_URL}/subscribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, cadence }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail || `Subscription failed: ${res.status}`)
  }
  return res.json()
}
