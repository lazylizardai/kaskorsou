// Cloudflare Pages Function — video streaming proxy for Supabase Storage.
//
// Waarom dit bestaat: Supabase Storage's publieke object-endpoint slicet
// Range-requests wél correct (content-length klopt met het gevraagde stuk),
// maar stuurt géén "Content-Range" response-header mee. Dat is een schending
// van de HTTP-spec voor 206-responses, en Chrome's <video>-engine stalt
// daarop stil (readyState blijft 0, networkState blijft LOADING, "stalled"
// event na ~3s, daarna niets meer — video lijkt te "spelen" maar buffert
// voor altijd).
//
// Deze proxy staat alléén een vaste bucket toe (geen open proxy/SSRF-risico):
// GET /video-proxy/<pad-in-bucket> -> Supabase Storage KasKorsou/<pad>.
// Hij forwardt de Range-header naar Supabase, en vult de ontbrekende
// Content-Range header zelf aan met behulp van de werkelijke totale
// bestandsgrootte (via een korte HEAD-call), zodat browsers weer normaal
// kunnen streamen/seeken.

const SUPABASE_BASE =
  'https://tbfjlfnahdqfbnpszyyj.supabase.co/storage/v1/object/public/KasKorsou/'

export async function onRequestGet(context) {
  const { request, params } = context
  const path = Array.isArray(params.path) ? params.path.join('/') : params.path
  if (!path) return new Response('Not found', { status: 404 })

  const upstreamUrl = SUPABASE_BASE + path
  const range = request.headers.get('Range')

  const upstreamResp = await fetch(upstreamUrl, {
    headers: range ? { Range: range } : {},
  })

  if (!upstreamResp.ok && upstreamResp.status !== 206) {
    return new Response('Upstream error', { status: upstreamResp.status })
  }

  const headers = new Headers(upstreamResp.headers)
  headers.set('Accept-Ranges', 'bytes')
  headers.set('Cache-Control', 'public, max-age=31536000, immutable')
  headers.delete('cache-control')
  headers.set('cache-control', 'public, max-age=31536000, immutable')

  let status = upstreamResp.status

  if (range && upstreamResp.status === 206 && !upstreamResp.headers.get('content-range')) {
    const match = /bytes=(\d+)-(\d*)/.exec(range)
    const sliceLen = parseInt(upstreamResp.headers.get('content-length') || '0', 10)
    if (match && sliceLen > 0) {
      const start = parseInt(match[1], 10)
      const end = start + sliceLen - 1
      // Totale bestandsgrootte ophalen: alleen nodig om de Content-Range
      // header kloppend te maken (browsers gebruiken dit voor duration/seek).
      const headResp = await fetch(upstreamUrl, { method: 'HEAD' })
      const total = headResp.headers.get('content-length')
      if (total) {
        headers.set('Content-Range', `bytes ${start}-${end}/${total}`)
      }
    }
  } else if (!range && upstreamResp.status === 200) {
    status = 200
  }

  return new Response(upstreamResp.body, { status, headers })
}

export async function onRequestHead(context) {
  const { params } = context
  const path = Array.isArray(params.path) ? params.path.join('/') : params.path
  if (!path) return new Response('Not found', { status: 404 })

  const upstreamUrl = SUPABASE_BASE + path
  const upstreamResp = await fetch(upstreamUrl, { method: 'HEAD' })
  const headers = new Headers(upstreamResp.headers)
  headers.set('Accept-Ranges', 'bytes')
  headers.set('cache-control', 'public, max-age=31536000, immutable')
  return new Response(null, { status: upstreamResp.status, headers })
}
