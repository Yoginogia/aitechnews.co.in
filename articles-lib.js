// lib/articles.js
// AI-generated articles ko read karne ka ek helper
// GitHub Actions se generate hue JSON files yahan se read honge

import fs   from 'fs'
import path from 'path'

const ARTICLES_DIR = path.join(process.cwd(), 'articles')

/** Sabhi articles ya filtered articles */
export function getAllArticles({ category, limit = 20, offset = 0, tag } = {}) {
  try {
    const indexPath = path.join(ARTICLES_DIR, 'index.json')
    if (!fs.existsSync(indexPath)) return []

    let list = JSON.parse(fs.readFileSync(indexPath, 'utf8'))

    if (category) list = list.filter(a => a.category?.toLowerCase() === category.toLowerCase())
    if (tag)      list = list.filter(a => a.tags?.some(t => t.toLowerCase() === tag.toLowerCase()))

    return list.slice(offset, offset + limit)
  } catch { return [] }
}

/** Single article by slug */
export function getArticleBySlug(slug) {
  try {
    const fp = path.join(ARTICLES_DIR, `${slug}.json`)
    if (!fs.existsSync(fp)) return null
    return JSON.parse(fs.readFileSync(fp, 'utf8'))
  } catch { return null }
}

/** Sab slugs — generateStaticParams ke liye */
export function getAllSlugs() {
  try {
    const indexPath = path.join(ARTICLES_DIR, 'index.json')
    if (!fs.existsSync(indexPath)) return []
    return JSON.parse(fs.readFileSync(indexPath, 'utf8')).map(a => a.slug)
  } catch { return [] }
}

/** Related articles (same category, different slug) */
export function getRelatedArticles(slug, category, limit = 3) {
  return getAllArticles({ category, limit: limit + 1 }).filter(a => a.slug !== slug).slice(0, limit)
}

/** Latest N articles — homepage ke liye */
export function getLatestArticles(n = 6) {
  return getAllArticles({ limit: n })
}
