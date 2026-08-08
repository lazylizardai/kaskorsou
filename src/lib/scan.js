// ─── 3D-scan helpers ─────────────────────────────────────────────────────────

// Heeft deze listing een actieve (niet-verlopen) 3D-scan?
export function hasActiveScan(listing) {
  if (!listing || listing.scan_status !== 'active') return false
  if (listing.scan_expires_at) return new Date(listing.scan_expires_at).getTime() > Date.now()
  return true
}

// Bouw een embed-URL voor de 3D-tour viewer.
// Bekende viewer-URL's worden direct gebruikt; anders wrappen we in de SuperSplat viewer.
export function buildScanEmbedUrl(scanUrl) {
  if (!scanUrl) return null
  const known = ['playcanvas.com', 'lumalabs.ai/embed', 'sketchfab.com/models/', '/viewer/', '/embed/']
  if (known.some(k => scanUrl.includes(k))) return scanUrl
  return `https://playcanvas.com/supersplat/viewer?load=${encodeURIComponent(scanUrl)}`
}
