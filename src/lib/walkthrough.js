// ─── Bezichtiging (walkthrough) helpers ────────────────────────────────────
// Derde product naast de échte 3D-scan (lib/scan.js) en de AI Video Tour
// (lib/video.js). De Bezichtiging is dezelfde AI-techniek als de Video Tour,
// maar anders bediend: de bezoeker sleept zelf door het huis, kamer voor
// kamer, en kan direct naar een ruimte springen. De video is bewust zonder
// geluid en met een keyframe op élk frame gecodeerd, anders springt het
// scrubben naar het dichtstbijzijnde keyframe en hakkelt het beeld.

export function hasWalkthrough(listing) {
  if (!listing) return false
  return listing.walkthrough_status === 'active' && !!listing.walkthrough_url
}

// Valt terug op één hoofdstuk als er geen kamerlijst is opgeslagen.
export function walkthroughChapters(listing) {
  const raw = listing?.walkthrough_chapters
  if (!Array.isArray(raw) || raw.length === 0) {
    return [{ t: 0, name: 'Bezichtiging', sub: listing?.title || '' }]
  }
  return raw
    .filter(c => c && typeof c.t === 'number' && c.name)
    .sort((a, b) => a.t - b.t)
}

export function walkthroughMusicUrl(listing) {
  const key = listing?.walkthrough_music
  if (!key) return null
  return `/video-proxy/music/${key}.m4a`
}
