// components/LatestArticlesSection.jsx
// Apne homepage pe yeh component add karo
// Latest 6 AI-generated articles show karta hai

import { getLatestArticles } from '@/lib/articles'
import Link from 'next/link'
import Image from 'next/image'

const CAT_COLORS = {
  'AI Tools':         'bg-purple-100 text-purple-700',
  'Gadgets':          'bg-blue-100   text-blue-700',
  'Software Updates': 'bg-green-100  text-green-700',
  'Crypto':           'bg-yellow-100 text-yellow-700',
  'Best Phones':      'bg-pink-100   text-pink-700',
}

export default function LatestArticlesSection() {
  const articles = getLatestArticles(6)

  if (articles.length === 0) return null

  const [featured, ...rest] = articles

  return (
    <section className="max-w-6xl mx-auto px-4 py-10">

      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            🔥 Aaj Ki Khabrein
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            AI se auto-updated · Roz subah 7 AM
          </p>
        </div>
        <Link href="/blog"
          className="text-sm font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1">
          Sab dekho →
        </Link>
      </div>

      {/* Featured + Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* Featured Article (big) */}
        <Link href={`/blog/${featured.slug}`}
          className="group lg:col-span-2 bg-white rounded-2xl overflow-hidden shadow-sm
                     hover:shadow-lg transition-all border border-gray-100">
          <div className="relative h-56 bg-gradient-to-br from-blue-50 to-indigo-100">
            <Image
              src={featured.image || '/images/blog/default.jpg'}
              alt={featured.title}
              fill className="object-cover group-hover:scale-105 transition-transform duration-500"
            />
            <span className={`absolute top-3 left-3 text-xs font-bold px-2.5 py-1 rounded-full
              ${CAT_COLORS[featured.category] || 'bg-gray-100 text-gray-700'}`}>
              {featured.category}
            </span>
          </div>
          <div className="p-5">
            <h3 className="font-bold text-gray-900 text-lg leading-snug mb-2
                           group-hover:text-blue-600 transition-colors">
              {featured.title}
            </h3>
            <p className="text-gray-500 text-sm line-clamp-2 mb-3">{featured.excerpt}</p>
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span>📅 {featured.date}</span>
              <span>⏱ {featured.readTime}</span>
              <span className="ml-auto text-blue-500 font-semibold">Padho →</span>
            </div>
          </div>
        </Link>

        {/* Side articles (small) */}
        <div className="flex flex-col gap-4">
          {rest.slice(0, 4).map(article => (
            <Link key={article.slug} href={`/blog/${article.slug}`}
              className="group flex gap-3 bg-white rounded-xl p-3 hover:shadow-md
                         transition-all border border-gray-100">
              <div className="relative w-20 h-20 flex-shrink-0 rounded-lg overflow-hidden bg-gray-100">
                <Image
                  src={article.image || '/images/blog/default.jpg'}
                  alt={article.title} fill className="object-cover"
                />
              </div>
              <div className="flex-1 min-w-0">
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded
                  ${CAT_COLORS[article.category] || 'bg-gray-100 text-gray-700'}`}>
                  {article.category}
                </span>
                <h4 className="text-xs font-semibold text-gray-900 line-clamp-2 mt-1
                               group-hover:text-blue-600 transition-colors leading-snug">
                  {article.title}
                </h4>
                <span className="text-[10px] text-gray-400 mt-1 block">{article.date}</span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
