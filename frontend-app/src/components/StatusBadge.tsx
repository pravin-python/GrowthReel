import type { LeadStatus, PostStatus } from '../lib/types'

const LEAD_STYLES: Record<LeadStatus, string> = {
  new: 'bg-sky-100 text-sky-700 ring-sky-600/20',
  contacted: 'bg-amber-100 text-amber-700 ring-amber-600/20',
  qualified: 'bg-violet-100 text-violet-700 ring-violet-600/20',
  won: 'bg-emerald-100 text-emerald-700 ring-emerald-600/20',
  lost: 'bg-rose-100 text-rose-700 ring-rose-600/20',
}

const POST_STYLES: Record<PostStatus, string> = {
  draft: 'bg-slate-100 text-slate-700 ring-slate-600/20',
  published: 'bg-emerald-100 text-emerald-700 ring-emerald-600/20',
  archived: 'bg-rose-100 text-rose-700 ring-rose-600/20',
}

function Badge({ label, className }: { label: string; className: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${className}`}
    >
      {label}
    </span>
  )
}

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return <Badge label={status} className={LEAD_STYLES[status]} />
}

export function PostStatusBadge({ status }: { status: PostStatus }) {
  return <Badge label={status} className={POST_STYLES[status]} />
}
