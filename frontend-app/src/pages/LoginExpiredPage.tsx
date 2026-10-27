const MARKETING_SITE_URL = import.meta.env.VITE_MARKETING_SITE_URL || 'http://localhost:8000'

export function LoginExpiredPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-rose-100">
          <span className="text-xl text-rose-600">!</span>
        </div>
        <h1 className="text-lg font-semibold text-slate-900">Your sign-in link expired</h1>
        <p className="mt-2 text-sm text-slate-500">
          The link used to sign you into GrowthReel is no longer valid — it may have expired, already been used, or
          your session may have timed out. Please sign in again to continue.
        </p>
        <a
          href={`${MARKETING_SITE_URL}/accounts/login/`}
          className="mt-6 inline-flex w-full items-center justify-center rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500"
        >
          Back to sign in
        </a>
      </div>
    </div>
  )
}
