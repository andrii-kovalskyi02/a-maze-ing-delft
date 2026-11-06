-- The shared scoreboard's table. Paste this into the Supabase SQL Editor and run it once.
-- Anyone with the public key can read scores and add one; nobody can change or delete them.
-- (You can still delete a row yourself from the Supabase dashboard.)

create table scores (
  run_id uuid primary key,
  name text not null check (char_length(name) between 1 and 30),
  player_tag text check (char_length(player_tag) <= 16),
  percent int not null check (percent between 0 and 100),
  seconds real not null check (seconds > 0),
  created_at timestamptz default now()
);

alter table scores enable row level security;
create policy "anyone can read" on scores for select using (true);
create policy "anyone can add" on scores for insert with check (true);

-- A table made before player tags existed: run this once to add the column.
-- alter table scores add column player_tag text check (char_length(player_tag) <= 16);
