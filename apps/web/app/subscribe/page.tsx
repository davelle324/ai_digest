import NavBar from '@/components/NavBar'
import SubscribeForm from '@/components/SubscribeForm'

export const metadata = {
  title: 'Subscribe — AI Digest',
  description: 'Get the latest AI/ML news delivered to your inbox.',
}

export default function SubscribePage() {
  return (
    <div className="min-h-screen flex flex-col">
      <NavBar />
      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-3xl font-bold text-white mb-2">Stay in the loop</h1>
            <p className="text-gray-400">
              Get curated AI/ML news delivered to your inbox — daily or weekly.
            </p>
          </div>
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
            <SubscribeForm />
          </div>
        </div>
      </main>
    </div>
  )
}
