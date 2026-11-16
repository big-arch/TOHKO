-- Reviewable setup SQL. Apply through a tracked Supabase migration before deploy.
-- This file does not change any existing application tables or authentication.
begin;

create schema if not exists tonko_private;
revoke all on schema tonko_private from public, anon, authenticated;
grant usage on schema tonko_private to service_role;

create table if not exists tonko_private.assistant_limits (
  id boolean primary key default true check (id),
  global_daily integer not null default 250 check (global_daily between 1 and 10000),
  global_minute integer not null default 12 check (global_minute between 1 and 100),
  identity_daily integer not null default 24 check (identity_daily between 1 and 1000),
  identity_minute integer not null default 3 check (identity_minute between 1 and 20)
);
insert into tonko_private.assistant_limits (id) values (true) on conflict do nothing;

create table if not exists tonko_private.assistant_usage (
  scope text not null,
  bucket timestamptz not null,
  used integer not null default 0 check (used >= 0),
  expires_at timestamptz not null,
  primary key (scope, bucket)
);
create index if not exists assistant_usage_expiry on tonko_private.assistant_usage (expires_at);
alter table tonko_private.assistant_limits enable row level security;
alter table tonko_private.assistant_usage enable row level security;
revoke all on tonko_private.assistant_limits, tonko_private.assistant_usage from public, anon, authenticated;
grant select on tonko_private.assistant_limits to service_role;
grant select, insert, update, delete on tonko_private.assistant_usage to service_role;

create or replace function public.tonko_assistant_quota(p_identity text, p_probe boolean default false)
returns table (allowed boolean, retry_after integer, reason text)
language plpgsql security invoker
set search_path = ''
as $$
declare
  v_now timestamptz := pg_catalog.clock_timestamp();
  v_day timestamptz := pg_catalog.date_trunc('day', v_now at time zone 'UTC') at time zone 'UTC';
  v_minute timestamptz := pg_catalog.date_trunc('minute', v_now);
  v_limits tonko_private.assistant_limits%rowtype;
  v_check record;
  v_count integer;
begin
  select * into strict v_limits from tonko_private.assistant_limits where id = true;
  if p_probe then
    -- No usage is reserved by readiness probes.
    return query select true, 0, 'ready'::text;
    return;
  end if;
  if p_identity is null or p_identity !~ '^[a-f0-9]{64}$' then
    raise exception 'Invalid quota identity' using errcode = '22023';
  end if;

  -- Every isolate and region uses the same lock. All four budgets are checked
  -- and reserved in one transaction, before the paid provider request.
  perform pg_catalog.pg_advisory_xact_lock(77290213, 1);
  delete from tonko_private.assistant_usage where expires_at < v_now - interval '1 day';
  for v_check in
    select * from (values
      ('global_day', v_day, v_day + interval '1 day', v_limits.global_daily),
      ('global_minute', v_minute, v_minute + interval '1 minute', v_limits.global_minute),
      ('identity_day:' || p_identity, v_day, v_day + interval '1 day', v_limits.identity_daily),
      ('identity_minute:' || p_identity, v_minute, v_minute + interval '1 minute', v_limits.identity_minute)
    ) as checks(scope, bucket, expires_at, maximum)
  loop
    select coalesce((select u.used from tonko_private.assistant_usage u where u.scope = v_check.scope and u.bucket = v_check.bucket), 0) into v_count;
    if v_count >= v_check.maximum then
      return query select false, greatest(1, ceil(extract(epoch from (v_check.expires_at - v_now)))::integer), 'limit'::text;
      return;
    end if;
  end loop;

  insert into tonko_private.assistant_usage (scope, bucket, used, expires_at)
  values
    ('global_day', v_day, 1, v_day + interval '1 day'),
    ('global_minute', v_minute, 1, v_minute + interval '1 minute'),
    ('identity_day:' || p_identity, v_day, 1, v_day + interval '1 day'),
    ('identity_minute:' || p_identity, v_minute, 1, v_minute + interval '1 minute')
  on conflict (scope, bucket) do update set used = tonko_private.assistant_usage.used + 1;
  return query select true, 0, 'reserved'::text;
end;
$$;

revoke all on function public.tonko_assistant_quota(text, boolean) from public, anon, authenticated;
grant execute on function public.tonko_assistant_quota(text, boolean) to service_role;
comment on function public.tonko_assistant_quota(text, boolean) is 'TONKO public assistant cost guard. Service role only; no message text or raw IP addresses are stored.';
notify pgrst, 'reload schema';
commit;
