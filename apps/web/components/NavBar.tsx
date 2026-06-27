import Link from 'next/link'

export default function NavBar() {
  return (
    <nav className="bg-gray-900 border-b border-gray-800">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link
            href="/"
            className="text-white text-xl font-bold tracking-tight hover:text-indigo-400 transition-colors"
          >
            AI Digest
          </Link>
          <Link
            href="/subscribe"
            className="inline-flex items-center px-4 py-2 rounded-md text-sm font-medium
                       bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
          >
            Subscribe
          </Link>
        </div>
      </div>
    </nav>
  )
}
