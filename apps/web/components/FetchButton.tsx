'use client'

import { useState, useTransition } from 'react'
import { triggerFetch } from '@/app/actions'

export default function FetchButton() {
  const [isPending, startTransition] = useTransition()
  const [message, setMessage] = useState<string | null>(null)

  function handleClick() {
    setMessage(null)
    startTransition(async () => {
      const result = await triggerFetch()
      setMessage(result.message)
    })
  }

  return (
    <div className="flex items-center gap-3">
      <button
        onClick={handleClick}
        disabled={isPending}
        className="px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium transition-colors"
      >
        {isPending ? 'Fetching…' : 'Fetch News'}
      </button>
      {message && (
        <span className="text-sm text-gray-400">{message}</span>
      )}
    </div>
  )
}
