import { useRef, type MouseEvent, type ReactNode } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const MARKETING_SITE_URL = import.meta.env.VITE_MARKETING_SITE_URL || 'http://localhost:8000'

const navItems = [
  { to: '/dashboard', label: 'Dashboard', end: true, icon: <GridIcon /> },
  { to: '/dashboard/leads', label: 'Leads', icon: <UsersIcon /> },
  { to: '/dashboard/posts', label: 'Posts', icon: <DocumentIcon /> },
]

function GridIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth={1.8}>
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  )
}

function UsersIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth={1.8}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M2.5 20c0-3.4 2.9-6 6.5-6s6.5 2.6 6.5 6" strokeLinecap="round" />
      <circle cx="17" cy="7.5" r="2.6" />
      <path d="M15.3 14.3c2.9.4 5.2 2.7 5.2 5.7" strokeLinecap="round" />
    </svg>
  )
}

function DocumentIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth={1.8}>
      <path d="M6 3h8l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" />
      <path d="M14 3v5h5" />
      <path d="M8 13h8M8 17h5" strokeLinecap="round" />
    </svg>
  )
}

function TiltNavLink({ to, end, label, icon }: { to: string; end?: boolean; label: string; icon: ReactNode }) {
  const ref = useRef<HTMLAnchorElement>(null)

  const handleMouseMove = (event: MouseEvent<HTMLAnchorElement>) => {
    const el = ref.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    const x = event.clientX - rect.left
    const y = event.clientY - rect.top
    const rotateX = ((y - rect.height / 2) / rect.height) * -12
    const rotateY = ((x - rect.width / 2) / rect.width) * 12
    el.style.transform = `perspective(500px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(6px)`
  }

  const handleMouseLeave = () => {
    const el = ref.current
    if (!el) return
    el.style.transform = 'perspective(500px) rotateX(0deg) rotateY(0deg) translateZ(0px)'
  }

  return (
    <NavLink
      ref={ref}
      to={to}
      end={end}
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      className={({ isActive }) =>
        `nav-tilt group flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium ${
          isActive
            ? 'active-gradient bg-gradient-to-r from-brand-blue to-brand-mint text-white shadow-[0_10px_24px_-8px_rgba(15,252,190,0.65)]'
            : 'text-white/70 hover:bg-white/10 hover:text-white'
        }`
      }
    >
      <span
        className={
          'flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 transition-colors group-hover:bg-white/20'
        }
      >
        {icon}
      </span>
      {label}
    </NavLink>
  )
}

export function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    window.location.href = `${MARKETING_SITE_URL}/accounts/login/`
  }

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="sidebar-3d relative flex w-72 flex-col overflow-hidden border-r border-white/10 bg-gradient-to-b from-[#0a1830] via-[#0d2a56] to-brand-blue text-white shadow-2xl">
        <div
          className="sidebar-orb -top-16 -left-16 h-56 w-56 bg-brand-mint/30"
          style={{ animation: 'orb-float-1 8s ease-in-out infinite' }}
        />
        <div
          className="sidebar-orb -right-20 bottom-10 h-64 w-64 bg-brand-blue/50"
          style={{ animation: 'orb-float-2 10s ease-in-out infinite' }}
        />

        <div className="relative z-10 flex h-20 items-center gap-3 border-b border-white/10 px-6">
          <div
            className="logo-3d flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-blue to-brand-mint shadow-[0_0_22px_rgba(15,252,190,0.6)]"
          >
            <span className="text-lg font-bold text-white">G</span>
          </div>
          <span className="text-lg font-semibold tracking-wide text-white">GrowthReel</span>
        </div>

        <nav className="relative z-10 flex-1 space-y-2 px-4 py-6">
          {navItems.map((item) => (
            <TiltNavLink key={item.to} to={item.to} end={item.end} label={item.label} icon={item.icon} />
          ))}
        </nav>

        <div className="relative z-10 border-t border-white/10 p-4">
          <div className="mb-3 flex items-center gap-3 rounded-xl bg-white/5 p-3 backdrop-blur-sm">
            <div
              className="h-9 w-9 shrink-0 rounded-full bg-gradient-to-br from-brand-mint to-brand-blue shadow-[0_0_16px_rgba(15,252,190,0.7)]"
              style={{ animation: 'glow-pulse 2.5s ease-in-out infinite' }}
            />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-white">
                {user ? `${user.first_name} ${user.last_name}` : 'Account'}
              </p>
              <p className="truncate text-xs text-white/60">{user?.email}</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void handleLogout()}
            className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-white/70 transition-colors hover:bg-white/10 hover:text-white"
          >
            Log out
          </button>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-8">
          <h1 className="text-base font-semibold text-slate-900">Welcome back{user ? `, ${user.first_name}` : ''}</h1>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-brand-blue hover:bg-brand-blue/10"
          >
            Home
          </button>
        </header>
        <div className="mx-auto max-w-6xl px-8 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
