'use client'

import { useRouter, useSearchParams } from 'next/navigation'
import { useCallback, useEffect, useRef, useState } from 'react'

interface SearchBarProps {
  defaultValue?: string
}

export default function SearchBar({ defaultValue = '' }: SearchBarProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [value, setValue] = useState(defaultValue)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    setValue(searchParams.get('q') ?? '')
  }, [searchParams])

  const push = useCallback(
    (q: string) => {
      const params = new URLSearchParams()
      if (q) params.set('q', q)
      router.push(q ? `/?${params.toString()}` : '/')
    },
    [router]
  )

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const q = e.target.value
    setValue(q)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => push(q), 300)
  }

  function handleClear() {
    setValue('')
    router.push('/')
  }

  return (
    <div className="relative w-full max-w-sm">
      <svg
        className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none"
        fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 111 11a6 6 0 0116 0z" />
      </svg>
      <input
        type="text"
        value={value}
        onChange={handleChange}
        placeholder="Search articles…"
        className="w-full bg-gray-800 border border-gray-700 rounded-md pl-9 pr-8 py-2 text-sm
                   text-white placeholder-gray-500 focus:outline-none focus:ring-2
                   focus:ring-indigo-500 focus:border-transparent transition"
      />
      {value && (
        <button
          onClick={handleClear}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
        >
          ✕
        </button>
      )}
    </div>
  )
}
