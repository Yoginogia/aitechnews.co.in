// app/blog/[slug]/page.jsx
// Single article page — /blog/chatgpt-new-feature-2026 type URLs

import { getArticleBySlug, getAllSlugs, getRelatedArticles } from '@/lib/articles'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'

// Static pages generate karo build time pe
export async function generateStaticParams() {
  const slugs = getAllSlugs()
  return slugs.map(slug => ({ slug }))
}

// SEO metadata
export async function generateMetadata({ params }) {
  const article = getArticleBySlug(params.slug)
  if (!article) return { title: 'Article Not Found' }

  return {
    title:       article.metaTitle || article.title,
    description: article.metaDescription || article.excerpt,
    openGraph: {
      title:       article.title,
      description: article.excerpt,
      images:      [{ url: article.image || '/images/og-default.jpg' }],
      type:        'article',
      publishedTime: article.date,
    },
    twitter: {
      card:        'summary_large_image',
      title:       article.title,
      description: article.excerpt,
    }
  }
}

const CAT_COLORS = {
  'AI Tools':         'bg-purple-100 text-purple-700 border-purple-200',
  'Gadgets':          'bg-blue-100   text-blue-700   border-blue-200',
  'Software Updates': 'bg-green-100  text-green-700  border-green-200',
  'Crypto':           'bg-yellow-100 text-yellow-700 border-yellow-200',
  'Best Phones':      'bg-pink-100   text-pink-700   border-pink-200',
}

export default function ArticlePage({ params }) {
  const article = getArticleBySlug(params.slug)
  if (!article) notFound()

  const related = getRelatedArticles(article.slug, article.category, 3)
  const catClass = CAT_COLORS[article.category] || 'bg-gray-100 text-gray-700 border-gray-200'

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">

      {/* Breadcrumb */}
      <nav className="text-sm text-gray-500 mb-6 flex items-center gap-2">
        <Link href="/" className="hover:text-blue-600">Home</Link>
        <span>›</span>
        <Link href="/blog" className="hover:text-blue-600">Blog</Link>
        <span>›</span>
        <Link href={`/blog?category=${article.category}`} className="hover:text-blue-600">
          {article.category}
        </Link>
      </nav>

      <article>
        {/* Category Badge */}
        <span className={`inline-block text-xs font-bold px-3 py-1 rounded-full border mb-4 ${catClass}`}>
          {article.category}
        </span>

        {/* Title */}
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-900 leading-tight mb-4">
          {article.title}
        </h1>

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 mb-6 pb-6 border-b">
          <span className="flex items-center gap-1">
            <span>📅</span> {article.date}
          </span>
          <span className="flex items-center gap-1">
            <span>⏱</span> {article.readTime}
          </span>
          <span className="flex items-center gap-1">
            <span>🤖</span> AI Generated · AITechNews Editorial
          </span>
          {article.source && (
            <a href={article.sourceUrl} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-blue-500 hover:underline">
              <span>🔗</span> Source: {article.source}
            </a>
          )}
        </div>

        {/* Hero Image */}
        {article.image && (
          <div className="relative w-full h-64 sm:h-80 rounded-xl overflow-hidden mb-8 bg-gradient-to-br from-blue-50 to-indigo-100">
            <Image
              src={article.image}
              alt={article.title}
              fill
              className="object-cover"
              priority
            />
          </div>
        )}

        {/* Article Content */}
        <div
          className="prose prose-gray prose-sm sm:prose max-w-none
            prose-h2:text-xl prose-h2:font-bold prose-h2:mt-8 prose-h2:mb-3
            prose-h3:text-lg prose-h3:font-semibold
            prose-p:leading-relaxed prose-p:text-gray-700
            prose-strong:text-gray-900
            prose-ul:my-3 prose-li:my-1
            prose-a:text-blue-600 prose-a:no-underline hover:prose-a:underline"
          dangerouslySetInnerHTML={{ __html: article.content }}
        />

        {/* Tags */}
        {article.tags?.length > 0 && (
          <div className="mt-8 pt-6 border-t">
            <div className="flex flex-wrap gap-2">
              {article.tags.map(tag => (
                <span key={tag}
                  className="px-3 py-1 bg-gray-100 text-gray-600 text-xs rounded-full">
                  #{tag}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Disclaimer */}
        <div className="mt-8 p-4 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
          <strong>📌 Disclaimer:</strong> Yeh article AI dwara automatically generate kiya gaya hai.
          Information accurate rakhne ki koshish ki gayi hai, par kisi bhi decision se pehle
          original source check karna recommended hai.
        </div>
      </article>

      {/* Related Articles */}
      {related.length > 0 && (
        <section className="mt-12">
          <h2 className="text-xl font-bold text-gray-900 mb-4">
            🔗 Related Articles
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {related.map(rel => (
              <Link key={rel.slug} href={`/blog/${rel.slug}`}
                className="p-4 bg-white border border-gray-100 rounded-xl hover:shadow-md
                           hover:border-blue-200 transition-all group">
                <span className="text-xs font-bold text-blue-600 block mb-1">{rel.category}</span>
                <h3 className="text-sm font-semibold text-gray-900 line-clamp-2
                               group-hover:text-blue-600 transition-colors">
                  {rel.title}
                </h3>
                <span className="text-xs text-gray-400 mt-2 block">{rel.date}</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Back button */}
      <div className="mt-10">
        <Link href="/blog"
          className="inline-flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-800">
          ← Back to All Articles
        </Link>
      </div>
    </div>
  )
}
