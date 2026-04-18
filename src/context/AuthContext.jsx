import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { supabase, getFavoriteIds, toggleFavorite as sbToggle } from '../lib/supabase'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [session, setSession] = useState(null)
  const [loading, setLoading] = useState(true)
  const [favoriteIds, setFavoriteIds] = useState(new Set())

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session)
      setUser(data.session?.user ?? null)
      setLoading(false)
    })
    const { data: listener } = supabase.auth.onAuthStateChange((_event, sess) => {
      setSession(sess)
      setUser(sess?.user ?? null)
    })
    return () => listener.subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (user?.id) {
      getFavoriteIds(user.id).then(setFavoriteIds)
    } else {
      setFavoriteIds(new Set())
    }
  }, [user?.id])

  const toggleFavorite = useCallback(async (listingId, requireAuth) => {
    if (!user) { requireAuth?.(); return false }
    const added = await sbToggle(user.id, listingId)
    setFavoriteIds(prev => {
      const next = new Set(prev)
      added ? next.add(listingId) : next.delete(listingId)
      return next
    })
    return added
  }, [user])

  return (
    <AuthContext.Provider value={{ user, session, loading, favoriteIds, toggleFavorite }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
