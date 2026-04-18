import { createClient } from '@supabase/supabase-js'
import { MOCK_LISTINGS } from '../data/mockListings'

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL || 'https://tbfjlfnahdqfbnpszyyj.supabase.co'
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY || ''

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)

// ─── Helpers ────────────────────────────────────────────────────────────────

// Supabase geeft numerieke velden terug als strings — normaliseer ze
function normalizeListings(rows) {
  return rows.map(l => ({
    ...l,
    price: l.price != null ? Number(l.price) : null,
    area_sqm: l.area_sqm != null ? Number(l.area_sqm) : null,
    latitude: l.latitude != null ? Number(l.latitude) : null,
    longitude: l.longitude != null ? Number(l.longitude) : null,
    bedrooms: l.bedrooms != null ? Number(l.bedrooms) : null,
    bathrooms: l.bathrooms != null ? Number(l.bathrooms) : null,
  }))
}

async function withMockFallback(query, mockData) {
  try {
    const { data, error } = await query
    if (error) throw error
    return data?.length ? normalizeListings(data) : mockData
  } catch (e) {
    console.warn('[KasKorsou] Supabase query failed, using mock data:', e.message)
    return mockData
  }
}

// ─── Listings ────────────────────────────────────────────────────────────────
export async function getListings(filters = {}) {
  let query = supabase.from('kas_active_listings').select('*')
  if (filters.listing_type) query = query.eq('listing_type', filters.listing_type)
  if (filters.property_type) query = query.eq('property_type', filters.property_type)
  if (filters.neighborhood) query = query.eq('neighborhood', filters.neighborhood)
  if (filters.min_price) query = query.gte('price', filters.min_price)
  if (filters.max_price) query = query.lte('price', filters.max_price)
  if (filters.bedrooms) query = query.gte('bedrooms', filters.bedrooms)
  return withMockFallback(query, MOCK_LISTINGS)
}

export async function getListingById(id) {
  const query = supabase.from('kas_listings').select('*').eq('id', id).single()
  return withMockFallback(query, MOCK_LISTINGS.find(l => l.id === id) || null)
}

export async function getSourceStats() {
  const { data } = await supabase.from('kas_source_stats').select('*')
  return data || []
}

// ─── Auth ────────────────────────────────────────────────────────────────────
export async function signUp({ email, password, fullName, phone }) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options: { data: { full_name: fullName, phone } },
  })
  if (error) throw error
  // upsert profile row
  if (data.user) {
    await supabase.from('kas_profiles').upsert({
      id: data.user.id,
      full_name: fullName,
      phone: phone || null,
    })
  }
  return data
}

export async function signIn({ email, password }) {
  const { data, error } = await supabase.auth.signInWithPassword({ email, password })
  if (error) throw error
  return data
}

export async function signOut() {
  const { error } = await supabase.auth.signOut()
  if (error) throw error
}

export async function getSession() {
  const { data } = await supabase.auth.getSession()
  return data.session
}

export async function updateProfile({ fullName, phone, avatarUrl }) {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) throw new Error('Not authenticated')
  const { error } = await supabase.from('kas_profiles').upsert({
    id: user.id,
    full_name: fullName,
    phone: phone || null,
    avatar_url: avatarUrl || null,
    updated_at: new Date().toISOString(),
  })
  if (error) throw error
}

// ─── Favorites ───────────────────────────────────────────────────────────────
export async function getFavorites(userId) {
  const { data, error } = await supabase
    .from('kas_favorites')
    .select('listing_id, kas_listings(*)')
    .eq('user_id', userId)
  if (error) throw error
  return data || []
}

export async function toggleFavorite(userId, listingId) {
  // check if exists
  const { data: existing } = await supabase
    .from('kas_favorites')
    .select('id')
    .eq('user_id', userId)
    .eq('listing_id', listingId)
    .single()

  if (existing) {
    await supabase.from('kas_favorites').delete()
      .eq('user_id', userId).eq('listing_id', listingId)
    return false // removed
  } else {
    await supabase.from('kas_favorites').insert({ user_id: userId, listing_id: listingId })
    return true // added
  }
}

export async function getFavoriteIds(userId) {
  if (!userId) return new Set()
  const { data } = await supabase
    .from('kas_favorites')
    .select('listing_id')
    .eq('user_id', userId)
  return new Set((data || []).map(r => r.listing_id))
}
