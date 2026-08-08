import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute'
import Navbar from './components/Navbar'
import Sidebar from './components/Sidebar'
import BackendStatusBanner from './components/BackendStatusBanner'
import Login from './pages/Login'
import ResidentDashboard from './pages/resident/Dashboard'
import RwaDashboard from './pages/rwa/Dashboard'
import GccDashboard from './pages/gcc/Dashboard'
import AdminDashboard from './pages/admin/Dashboard'

function Shell() { return <><Navbar/><div className="mx-auto flex min-h-[calc(100vh-73px)] max-w-7xl"><Sidebar/><main className="min-w-0 flex-1 p-5 md:p-8"><BackendStatusBanner/><Outlet/></main></div></> }
export default function App() { return <Routes><Route path="/login" element={<Login/>}/><Route element={<Shell/>}><Route path="/resident" element={<ProtectedRoute role="resident"><ResidentDashboard/></ProtectedRoute>}/><Route path="/rwa" element={<ProtectedRoute role="rwa"><RwaDashboard/></ProtectedRoute>}/><Route path="/gcc" element={<ProtectedRoute role="gcc"><GccDashboard/></ProtectedRoute>}/><Route path="/admin" element={<ProtectedRoute role="admin"><AdminDashboard/></ProtectedRoute>}/></Route><Route path="*" element={<Navigate to="/login" replace/>}/></Routes> }
