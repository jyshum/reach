-- backend/db/schema.sql
-- Run this in Supabase SQL Editor to create tables.

-- Users table (profile data, linked to Supabase Auth)
create table if not exists users (
  id uuid primary key,  -- matches auth.users.id
  email text not null,
  school text,
  grad_year int,
  skills text[] default '{}',
  location text,
  bio text,
  github_url text,
  portfolio_url text,
  tier text not null default 'free' check (tier in ('free', 'unlocked', 'paid')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Companies table (populated by pipeline)
create table if not exists companies (
  id serial primary key,
  name text unique not null,
  yc_batch text,
  description text,
  long_description text,
  summary text,
  one_liner text,
  website text,
  industry text,
  stage text,
  stage_detail text,
  technical_level text,
  team_size int,
  need_tags text[] default '{}',
  capability_tags text[] default '{}',
  specific_projects text[] default '{}',
  is_hiring boolean default false,
  status text,
  reachability_score text,
  reachability_probability float,
  founder_name text,
  founder_title text,
  founder_linkedin text,
  founder_twitter text,
  founder_avatar_url text,
  founder_email text,
  founder_email_status text default 'unknown',
  slug text,
  small_logo_url text,
  all_locations text,
  tags text[] default '{}',
  industries text[] default '{}',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Brief views (tracks which briefs a user has seen, enforces free tier limit)
create table if not exists brief_views (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  company_id int not null references companies(id) on delete cascade,
  viewed_at timestamptz not null default now(),
  unique(user_id, company_id)
);

-- Outreach log (tracks emails sent and outcomes)
create table if not exists outreach_log (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  company_id int not null references companies(id) on delete cascade,
  status text not null check (status in ('sent', 'replied', 'meeting', 'no-response', 'bounced')),
  sent_at timestamptz,
  followup_date timestamptz,
  notes text,
  created_at timestamptz not null default now()
);

-- Gmail OAuth tokens (encrypted, one per user)
create table if not exists gmail_tokens (
  user_id uuid primary key references users(id) on delete cascade,
  encrypted_refresh_token text not null,
  gmail_email text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Email log (tracks generated drafts, edits, and sends)
create table if not exists email_log (
  id serial primary key,
  user_id uuid not null references users(id) on delete cascade,
  company_id int not null references companies(id) on delete cascade,
  original_draft text not null,
  final_text text,
  subject_line text,
  tone text not null default 'curious',
  gmail_thread_id text,
  gmail_message_id text,
  status text not null default 'draft' check (status in ('draft', 'sent', 'replied', 'no_response', 'bounced')),
  sent_at timestamptz,
  reply_detected_at timestamptz,
  created_at timestamptz not null default now()
);

-- Indexes for common queries
create index if not exists idx_companies_reachability on companies(reachability_probability desc);
create index if not exists idx_companies_industry on companies(industry);
create index if not exists idx_brief_views_user on brief_views(user_id);
create index if not exists idx_outreach_user on outreach_log(user_id);
create index if not exists idx_email_log_user on email_log(user_id);
create index if not exists idx_email_log_status on email_log(status);
create index if not exists idx_email_log_thread on email_log(gmail_thread_id);

-- Auto-update updated_at on users
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create or replace trigger users_updated_at
  before update on users
  for each row execute function update_updated_at();

create or replace trigger companies_updated_at
  before update on companies
  for each row execute function update_updated_at();

create or replace trigger gmail_tokens_updated_at
  before update on gmail_tokens
  for each row execute function update_updated_at();

-- Enable Row Level Security
alter table users enable row level security;
alter table brief_views enable row level security;
alter table outreach_log enable row level security;

-- RLS policies: users can only read/write their own data
create policy "Users can view own profile" on users for select using (auth.uid() = id);
create policy "Users can update own profile" on users for update using (auth.uid() = id);
create policy "Users can insert own profile" on users for insert with check (auth.uid() = id);

-- Companies are readable by everyone (no auth needed for browsing)
-- No RLS on companies — they're public data

create policy "Users can view own brief_views" on brief_views for select using (auth.uid() = user_id);
create policy "Users can insert own brief_views" on brief_views for insert with check (auth.uid() = user_id);

create policy "Users can view own outreach" on outreach_log for select using (auth.uid() = user_id);
create policy "Users can insert own outreach" on outreach_log for insert with check (auth.uid() = user_id);
create policy "Users can update own outreach" on outreach_log for update using (auth.uid() = user_id);

-- Gmail tokens RLS
alter table gmail_tokens enable row level security;
create policy "Users can view own gmail_tokens" on gmail_tokens for select using (auth.uid() = user_id);
create policy "Users can insert own gmail_tokens" on gmail_tokens for insert with check (auth.uid() = user_id);
create policy "Users can update own gmail_tokens" on gmail_tokens for update using (auth.uid() = user_id);
create policy "Users can delete own gmail_tokens" on gmail_tokens for delete using (auth.uid() = user_id);

-- Email log RLS
alter table email_log enable row level security;
create policy "Users can view own email_log" on email_log for select using (auth.uid() = user_id);
create policy "Users can insert own email_log" on email_log for insert with check (auth.uid() = user_id);
create policy "Users can update own email_log" on email_log for update using (auth.uid() = user_id);

-- ============================================================
-- MIGRATION: Bounce detection (2026-06-01)
-- Run these in Supabase SQL Editor on existing database:
--
-- ALTER TABLE email_log DROP CONSTRAINT email_log_status_check;
-- ALTER TABLE email_log ADD CONSTRAINT email_log_status_check
--   CHECK (status IN ('draft', 'sent', 'replied', 'no_response', 'bounced'));
--
-- ALTER TABLE outreach_log DROP CONSTRAINT outreach_log_status_check;
-- ALTER TABLE outreach_log ADD CONSTRAINT outreach_log_status_check
--   CHECK (status IN ('sent', 'replied', 'meeting', 'no-response', 'bounced'));
--
-- ALTER TABLE companies ADD COLUMN IF NOT EXISTS
--   founder_email_status text DEFAULT 'unknown';
-- ============================================================
