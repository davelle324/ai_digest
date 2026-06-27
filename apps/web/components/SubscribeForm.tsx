'use client'

import { useState } from 'react'
import { subscribe } from '@/lib/api'

export default function SubscribeForm() {
  const [email, setEmail] = useState('')
  const [cadence, setCadence] = useState<'daily' | 'weekly'>('daily')
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setStatus('loading')
    setMessage('')

    try {
      const result = await subscribe(email, cadence)
      setStatus('success')
      setMessage(result.message)
      setEmail('')
    } catch (err) {
      setStatus('error')
      setMessage(err instanceof Error ? err.message : 'Something went wrong. Please try again.')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-md space-y-5">
      <div>
        <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
          Email address
        </label>
        <input
          id="email"
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="w-full px-4 py-2 rounded-md bg-gray-800 border border-gray-700
                     text-white placeholder-gray-500 focus:outline-none focus:ring-2
                     focus:ring-indigo-500 focus:border-transparent transition"
        />
      </div>

      <fieldset>
        <legend className="block text-sm font-medium text-gray-300 mb-2">Frequency</legend>
        <div className="flex gap-6">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="cadence"
              value="daily"
              checked={cadence === 'daily'}
              onChange={() => setCadence('daily')}
              className="accent-indigo-500"
            />
            <span className="text-gray-200 text-sm">Daily</span>
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="cadence"
              value="weekly"
              checked={cadence === 'weekly'}
              onChange={() => setCadence('weekly')}
              className="accent-indigo-500"
            />
            <span className="text-gray-200 text-sm">Weekly</span>
          </label>
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={status === 'loading'}
        className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60
                   text-white font-semibold rounded-md transition-colors focus:outline-none
                   focus:ring-2 focus:ring-indigo-400"
      >
        {status === 'loading' ? 'Subscribing…' : 'Subscribe'}
      </button>

      {status === 'success' && (
        <p className="text-green-400 text-sm text-center">{message}</p>
      )}
      {status === 'error' && (
        <p className="text-red-400 text-sm text-center">{message}</p>
      )}
    </form>
  )
}
