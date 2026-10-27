import { useEffect, useState } from 'react'
import { apiRequest } from '../lib/apiClient'
import { LeadStatusBadge } from '../components/StatusBadge'
import type { Lead, LeadStatus } from '../lib/types'

const STATUS_OPTIONS: LeadStatus[] = ['new', 'contacted', 'qualified', 'won', 'lost']

export function LeadsPage() {
  const [leads, setLeads] = useState<Lead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<LeadStatus | 'all'>('all')
  const [pendingIds, setPendingIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)

    const query = statusFilter === 'all' ? '' : `?status=${encodeURIComponent(statusFilter)}`
    void apiRequest<Lead[]>(`/leads${query}`).then((result) => {
      if (cancelled) return
      if (result.ok) {
        setLeads(result.data)
      } else {
        setError(result.error)
      }
      setLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [statusFilter])

  const handleStatusChange = async (lead: Lead, nextStatus: LeadStatus) => {
    const previous = lead.status
    // Optimistic update: flip the UI immediately, roll back if the PATCH fails.
    setLeads((current) => current.map((l) => (l.id === lead.id ? { ...l, status: nextStatus } : l)))
    setPendingIds((current) => new Set(current).add(lead.id))

    const result = await apiRequest<Lead>(`/leads/${lead.id}`, {
      method: 'PATCH',
      body: { status: nextStatus },
    })

    setPendingIds((current) => {
      const next = new Set(current)
      next.delete(lead.id)
      return next
    })

    if (!result.ok) {
      setLeads((current) => current.map((l) => (l.id === lead.id ? { ...l, status: previous } : l)))
      setError(`Couldn't update ${lead.name}: ${result.error}`)
      return
    }

    setLeads((current) => current.map((l) => (l.id === lead.id ? result.data : l)))
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">Leads</h2>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as LeadStatus | 'all')}
          className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        >
          <option value="all">All statuses</option>
          {STATUS_OPTIONS.map((status) => (
            <option key={status} value={status}>
              {status}
            </option>
          ))}
        </select>
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-2 text-sm text-rose-700">{error}</div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full divide-y divide-slate-200">
          <thead className="bg-slate-50">
            <tr>
              {['Name', 'Company', 'Email', 'Source', 'Status', 'Created', ''].map((heading) => (
                <th
                  key={heading}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500"
                >
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-sm text-slate-500">
                  Loading leads...
                </td>
              </tr>
            ) : leads.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-sm text-slate-500">
                  No leads match this filter.
                </td>
              </tr>
            ) : (
              leads.map((lead) => (
                <tr key={lead.id} className="hover:bg-slate-50">
                  <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-slate-900">{lead.name}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{lead.company ?? '-'}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{lead.email}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">{lead.source ?? '-'}</td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <LeadStatusBadge status={lead.status} />
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-500">
                    {new Date(lead.created_at).toLocaleDateString()}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3 text-sm">
                    <select
                      value={lead.status}
                      disabled={pendingIds.has(lead.id)}
                      onChange={(e) => void handleStatusChange(lead, e.target.value as LeadStatus)}
                      className="rounded-md border border-slate-300 bg-white px-2 py-1 text-xs text-slate-700 disabled:opacity-50"
                    >
                      {STATUS_OPTIONS.map((status) => (
                        <option key={status} value={status}>
                          {status}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
