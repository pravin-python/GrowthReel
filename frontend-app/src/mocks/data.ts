import type { CurrentUser, Lead, Post } from '../lib/types'

export const mockUser: CurrentUser = {
  id: 'user_1',
  email: 'demo@growthreel.com',
  first_name: 'Dana',
  last_name: 'Reel',
  role: 'admin',
}

export function seedLeads(): Lead[] {
  return [
    {
      id: 'lead_1',
      name: 'Avery Stone',
      email: 'avery@acme.test',
      phone: '555-0100',
      company: 'Acme Co',
      status: 'new',
      source: 'landing_page',
      owner_id: 'user_1',
      created_at: '2026-10-20T14:32:00Z',
    },
    {
      id: 'lead_2',
      name: 'Priya Kapoor',
      email: 'priya@globex.test',
      phone: '555-0101',
      company: 'Globex',
      status: 'contacted',
      source: 'referral',
      owner_id: 'user_1',
      created_at: '2026-10-21T09:12:00Z',
    },
    {
      id: 'lead_3',
      name: 'Jonas Mercer',
      email: 'jonas@initech.test',
      phone: null,
      company: 'Initech',
      status: 'qualified',
      source: 'webinar',
      owner_id: 'user_1',
      created_at: '2026-10-22T18:45:00Z',
    },
    {
      id: 'lead_4',
      name: 'Lena Fischer',
      email: 'lena@umbrella.test',
      phone: '555-0103',
      company: 'Umbrella Corp',
      status: 'lost',
      source: 'cold_outreach',
      owner_id: 'user_1',
      created_at: '2026-10-23T11:05:00Z',
    },
    {
      id: 'lead_5',
      name: 'Marcus Webb',
      email: 'marcus@soylent.test',
      phone: '555-0104',
      company: 'Soylent',
      status: 'won',
      source: 'landing_page',
      owner_id: 'user_1',
      created_at: '2026-10-24T08:20:00Z',
    },
  ]
}

export function seedPosts(): Post[] {
  return [
    {
      id: 'post_1',
      title: 'Welcome to GrowthReel',
      slug: 'welcome-to-growthreel',
      status: 'published',
      published_at: '2026-09-01T00:00:00Z',
      author_email: 'info@dolphinwebsolution.com',
    },
    {
      id: 'post_2',
      title: '5 CRM habits that compound',
      slug: '5-crm-habits-that-compound',
      status: 'published',
      published_at: '2026-09-15T00:00:00Z',
      author_email: 'info@dolphinwebsolution.com',
    },
    {
      id: 'post_3',
      title: 'Draft: Q4 roadmap preview',
      slug: 'q4-roadmap-preview',
      status: 'draft',
      published_at: null,
      author_email: 'info@dolphinwebsolution.com',
    },
  ]
}
