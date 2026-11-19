import { Navigate, Route, Routes, useParams } from 'react-router'
import type { ReactNode } from 'react'
import './App.css'
import AppLayout from './layouts/AppLayout'
import { isLoggedIn } from './lib/auth'
import Classroom from './pages/Classroom'
import Login from './pages/Login'
import NotebookHome from './pages/NotebookHome'
import Register from './pages/Register'
import ResourceCenter from './pages/ResourceCenter'
import Tutor from './pages/Tutor'
import UserProfile from './pages/UserProfile'

function ProtectedRoute({ children }: { children: ReactNode }) {
  return isLoggedIn() ? children : <Navigate to="/login" replace />
}

function LoginRoute() {
  return isLoggedIn() ? <Navigate to="/" replace /> : <Login />
}

function RegisterRoute() {
  return isLoggedIn() ? <Navigate to="/" replace /> : <Register />
}

function ClassroomRoute() {
  const { notebookId = 'default' } = useParams()
  return <Classroom key={notebookId} />
}

function App() {
  return (
    <Routes>
      <Route path="login" element={<LoginRoute />} />
      <Route path="register" element={<RegisterRoute />} />
      <Route
        index
        element={
          <ProtectedRoute>
            <NotebookHome />
          </ProtectedRoute>
        }
      />
      <Route
        path="notebooks/:notebookId"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="classroom" replace />} />
        <Route path="classroom" element={<ClassroomRoute />} />
        <Route path="resources" element={<ResourceCenter />} />
        <Route path="tutor" element={<Tutor />} />
        <Route path="profile" element={<UserProfile />} />
        <Route path="*" element={<Navigate to="classroom" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default App
