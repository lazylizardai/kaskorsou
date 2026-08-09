// ─── AI video-tour helpers ─────────────────────────────────────────────────
// Los van de échte 3D-scan (Matterport/Polycam/Luma, zie lib/scan.js): dit is
// een AI-gegenereerde cinematische video uit de listingfoto's. Twee aparte
// producten, twee aparte badges — nooit door elkaar presenteren.

export function hasVideoTour(listing) {
  if (!listing) return false
  return listing.video_status === 'active' && !!listing.video_url
}

// Supabase Storage's publieke endpoint mist de Content-Range response-header
// op partial (206) responses — Chrome's <video>-engine stalt daarop (blijft
// "bufferen" bij 0:00, speelt nooit af). We routeren daarom via een eigen
// Cloudflare Pages Function (/video-proxy/<pad>) die dezelfde bytes doorstuurt
// mét een correcte Content-Range header. Zie functions/video-proxy/[[path]].js.
const SUPABASE_VIDEO_MARKER = '/storage/v1/object/public/KasKorsou/'

export function buildVideoStreamUrl(videoUrl) {
  if (!videoUrl) return null
  const idx = videoUrl.indexOf(SUPABASE_VIDEO_MARKER)
  if (idx === -1) return videoUrl
  const path = videoUrl.slice(idx + SUPABASE_VIDEO_MARKER.length)
  return `/video-proxy/${path}`
}
