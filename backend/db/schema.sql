-- backend/db/schema.sql
-- Run this in Supabase SQL Editor to create tables.

-- Users table (profile data, linked to Supabase Auth)
create table if not exists users (
  id uuid primary key,  -- matches auth.users.id
  email text not null,
  school text,
  grad_year int,
  skills text[] default '{}',
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
  status text not null check (status in ('sent', 'replied', 'meeting', 'no-response')),
  sent_at timestamptz,
  followup_date timestamptz,
  notes text,
  created_at timestamptz not null default now()
);

-- Indexes for common queries
create index if not exists idx_companies_reachability on companies(reachability_probability desc);
create index if not exists idx_companies_industry on companies(industry);
create index if not exists idx_brief_views_user on brief_views(user_id);
create index if not exists idx_outreach_user on outreach_log(user_id);

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
