// app/blog/page.jsx
// Ye page /blog route handle karta hai — sab articles list karta hai

import { getAllArticles } from '@/lib/articles'
import Link from 'next/link'
import Image from 'next/image'

export const metadata = {
  title:       'Latest Tech & AI News | AITechNews',
  description: 'India ki latest AI tools, gadgets, aur tech ki khabrein — Hindi + English mein',
}

// Category colors
const CAT_COLORS = {
  'AI Tools':         'bg-purple-100 text-purple-700',
  'Gadgets':          'bg-blue-100   text-blue-700',
  'Software Updates': 'bg-green-100  text-green-700',
  'Crypto':           'bg-yellow-100 text-yellow-700',
  'Best Phones':      'bg-pink-100   text-pink-700',
}

export default function BlogPage({ searchParams }) {
  const page     = parseInt(searchParams?.page || '1')
  const category = searchParams?.category || null
  const perPage  = 12

  const articles = getAllArticles({
    category,
    limit:  perPage,
    offset: (page - 1) * perPage,
  })

  const total     = getAllArticles({ category }).length
  const totalPages = Math.ceil(total / perPage)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          {category ? `${category} News` : '🔥 Latest Tech News'}
        </h1>
        <p className="text-gray-500">
          {total} articles · Auto-updated daily by AI
        </p>
      </div>

      {/* Category Filter Bar */}
      <div className="flex gap-2 flex-wrap mb-8">
        {['All', 'AI Tools', 'Gadgets', 'Software Updates', 'Crypto', 'Best Phones'].map(cat => (
          <Link
            key={cat}
            href={cat === 'All' ? '/blog' : `/blog?category=${encodeURIComponent(cat)}`}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold transition-all
              ${(!category && cat === 'All') || category === cat
                ? 'bg-blue-600 text-white'
                : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
          >
            {cat}
          </Link>
        ))}
      </div>

      {/* Articles Grid */}
      {articles.length === 0 ? (
        <div className="text-center py-20 text-gray-400">
          <div className="text-5xl mb-4">📭</div>
          <p>Abhi koi article nahi hai. Kal subah check karo!</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
          {articles.map(article => (
            <ArticleCard key={article.slug} article={article} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          {page > 1 && (
            <Link href={`/blog?page=${page - 1}${category ? `&category=${category}` : ''}`}
              className="px-4 py-2 bg-gray-100 rounded-lg hover:bg-gray-200 text-sm font-medium">
              ← Prev
            </Link>
          )}
          <span className="px-4 py-2 text-sm text-gray-500">
            Page {page} of {totalPages}
          </span>
          {page < totalPages && (
            <Link href={`/blog?page=${page + 1}${category ? `&category=${category}` : ''}`}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium">
              Next →
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

function ArticleCard({ article }) {
  const catClass = CAT_COLORS[article.category] || 'bg-gray-100 text-gray-700'

  return (
    <Link href={`/blog/${article.slug}`}
      className="group bg-white rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-all border border-gray-100">

      {/* Thumbnail */}
      <div className="relative h-44 bg-gradient-to-br from-blue-50 to-indigo-100 overflow-hidden">
        <Image
          src={article.image || '/images/blog/default.jpg'}
          alt={article.title}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-300"
          onError={(e) => { e.target.src = '/images/blog/default.jpg' }}
        />
        <span className={`absolute top-2 left-2 text-xs font-bold px-2 py-0.5 rounded-full ${catClass}`}>
          {article.category}
        </span>
      </div>

      {/* Content */}
      <div className="p-4">
        <h2 className="font-bold text-gray-900 text-sm leading-snug mb-2 line-clamp-2
                       group-hover:text-blue-600 transition-colors">
          {article.title}
        </h2>
        <p className="text-gray-500 text-xs line-clamp-2 mb-3">
          {article.excerpt}
        </p>
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span>📅 {article.date}</span>
          <span>⏱ {article.readTime}</span>
        </div>
      </div>
    </Link>
  )
}
