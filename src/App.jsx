import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import Navigation from './components/Navigation'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import DetailPage from './pages/DetailPage'
import AccountPage from './pages/AccountPage'
import FavoritesPage from './pages/FavoritesPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Navigation />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/listing/:id" element={<DetailPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/favorites" element={<FavoritesPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
