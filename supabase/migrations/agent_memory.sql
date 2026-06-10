-- Agent memory table: persists conversation history across server restarts
create table if not exists agent_memory (
    id          uuid primary key default gen_random_uuid(),
    session_id  text        not null,
    agent_type  text        not null,
    project     text        not null default 'default',
    role        text        not null check (role in ('user', 'assistant')),
    content     text        not null,
    created_at  timestamptz not null default now()
);

create index if not exists agent_memory_session_idx on agent_memory (session_id, created_at);

-- Only the service role can read/write; anon gets nothing
alter table agent_memory enable row level security;

create policy "service role full access"
    on agent_memory
    for all
    to service_role
    using (true)
    with check (true);
