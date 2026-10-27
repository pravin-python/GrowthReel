import { useAuth } from '../context/AuthContext'
import { useNotifications } from '../hooks/useNotifications'

export function DashboardHomePage() {
  const { user } = useAuth()
  const { sessionId, messages, connected } = useNotifications()

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Signed in as</p>
          <p className="mt-1 truncate text-lg font-semibold text-slate-900">{user?.email ?? '-'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Role</p>
          <p className="mt-1 text-lg font-semibold capitalize text-slate-900">{user?.role ?? '-'}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <p className="text-sm text-slate-500">Notification channel</p>
          <p className="mt-1 flex items-center gap-2 text-lg font-semibold text-slate-900">
            <span className={`h-2.5 w-2.5 rounded-full ${connected ? 'bg-emerald-500' : 'bg-slate-300'}`} />
            {connected ? 'Connected' : 'Connecting...'}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-base font-semibold text-slate-900">Live notifications</h2>
          {sessionId && <span className="font-mono text-xs text-slate-400">session {sessionId}</span>}
        </div>
        {messages.length === 0 ? (
          <p className="text-sm text-slate-500">No notifications yet. They will appear here in real time.</p>
        ) : (
          <ul className="space-y-2">
            {[...messages].reverse().map((message, index) => (
              <li
                key={`${index}-${message}`}
                className="rounded-lg border border-slate-100 bg-slate-50 px-4 py-2.5 text-sm text-slate-700"
              >
                {message}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
