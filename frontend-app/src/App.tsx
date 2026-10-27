import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import { DashboardLayout } from './components/DashboardLayout'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { LoginExpiredPage } from './pages/LoginExpiredPage'
import { DashboardHomePage } from './pages/DashboardHomePage'
import { LeadsPage } from './pages/LeadsPage'
import { PostsPage } from './pages/PostsPage'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/auth/callback" element={<AuthCallbackPage />} />
        <Route path="/login-expired" element={<LoginExpiredPage />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<DashboardHomePage />} />
          <Route path="leads" element={<LeadsPage />} />
          <Route path="posts" element={<PostsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
