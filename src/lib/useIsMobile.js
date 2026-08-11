import { useEffect, useState } from 'react'

// Zelfde 768px-grens als de bestaande Tailwind `md:`-breakpoint, zodat JS-
// en CSS-gebaseerde responsive-logica altijd hetzelfde omslagpunt gebruiken.
const QUERY = '(max-width: 767px)'

export function useIsMobile() {
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(QUERY).matches : false
  )

  useEffect(() => {
    const mql = window.matchMedia(QUERY)
    const onChange = (e) => setIsMobile(e.matches)
    mql.addEventListener('change', onChange)
    return () => mql.removeEventListener('change', onChange)
  }, [])

  return isMobile
}
