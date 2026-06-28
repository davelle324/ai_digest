'use server'

export async function triggerFetch(): Promise<{ ok: boolean; message: string }> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const adminSecret = process.env.ADMIN_SECRET

  if (!adminSecret) {
    return { ok: false, message: 'ADMIN_SECRET is not configured' }
  }

  try {
    const res = await fetch(`${apiUrl}/admin/fetch`, {
      method: 'POST',
      headers: { 'X-Admin-Key': adminSecret },
      cache: 'no-store',
    })
    if (!res.ok) return { ok: false, message: `API error: ${res.status}` }
    const data = await res.json()
    return { ok: true, message: `Fetched ${data.new_articles} new articles` }
  } catch (err) {
    return { ok: false, message: `Failed to reach API: ${err}` }
  }
}
