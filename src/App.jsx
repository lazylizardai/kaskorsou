import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { VideoTourProvider } from './context/VideoTourContext'
import Navigation from './components/Navigation'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import DetailPage from './pages/DetailPage'
import AccountPage from './pages/AccountPage'
import FavoritesPage from './pages/FavoritesPage'
import MakelaarsPage from './pages/MakelaarsPage'
import VoorwaardenPage from './pages/VoorwaardenPage'
import PrivacyPage from './pages/PrivacyPage'
import HoeHetWerktPage from './pages/HoeHetWerktPage'
import NotFoundPage from './pages/NotFoundPage'

// Lazy: houdt maplibre-gl uit de hoofdbundle
const Kaart3DPage = lazy(() => import('./pages/Kaart3DPage'))

function KaartLoader() {
  return (
    <div style={{ minHeight: '100dvh', paddingTop: 72, background: 'linear-gradient(180deg, #EAF2F0 0%, #F5F0E8 100%)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <style>{`@keyframes kk-loadpulse { 0%,100% { opacity: 1; } 50% { opacity: 0.45; } }`}</style>
      <p style={{ fontSize: 15, fontWeight: 700, color: '#09090B', letterSpacing: '-0.01em', animation: 'kk-loadpulse 1.6s ease-in-out infinite' }}>
        Curaçao laden…
      </p>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
      <VideoTourProvider>
        <Navigation />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/listing/:id" element={<DetailPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
          <Route path="/makelaars" element={<MakelaarsPage />} />
          <Route path="/voorwaarden" element={<VoorwaardenPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/hoe-het-werkt" element={<HoeHetWerktPage />} />
          <Route path="/kaart" element={
            <Suspense fallback={<KaartLoader />}>
              <Kaart3DPage />
            </Suspense>
          } />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </VideoTourProvider>
      </AuthProvider>
    </BrowserRouter>
  )
}
