-- Player accounts. Paste this into the Supabase SQL Editor and run it once.
--
-- Nobody can read or write the players table directly, not even with the public key: the game only
-- calls the three functions below. Passwords are hashed with bcrypt on the server, so a hash never
-- leaves the database, and a name is locked for a minute after five wrong passwords in a row.

create extension if not exists pgcrypto with schema extensions;

create table players (
  name text primary key check (char_length(name) between 1 and 30),
  password_hash text not null,
  failed_attempts int not null default 0,
  locked_until timestamptz,
  created_at timestamptz not null default now()
);
create unique index players_name_ignoring_case on players (lower(name));

alter table players enable row level security;  -- and no policies: no direct access at all
revoke all on players from anon, authenticated;


-- Whether a name is registered.
create function player_exists(player_name text) returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.players where lower(name) = lower(player_name));
$$;


-- Register a name with its password. False if the name is taken.
create function register_player(player_name text, password text) returns boolean
language plpgsql security definer set search_path = '' as $$
begin
  if char_length(password) < 4 then  -- profiles.MIN_PASSWORD
    raise exception 'password too short';
  end if;
  insert into public.players (name, password_hash)
  values (player_name, extensions.crypt(password, extensions.gen_salt('bf')));
  return true;
exception when unique_violation then
  return false;
end;
$$;


-- Check a password: 'ok', 'wrong', or 'locked' (too many wrong ones in a row; wait a minute).
create function check_password(player_name text, password text) returns text
language plpgsql security definer set search_path = '' as $$
declare
  player public.players%rowtype;
begin
  select * into player from public.players where lower(name) = lower(player_name) for update;
  if not found then
    return 'wrong';
  end if;
  if player.locked_until > now() then
    return 'locked';
  end if;
  if player.password_hash = extensions.crypt(password, player.password_hash) then
    update public.players set failed_attempts = 0, locked_until = null where name = player.name;
    return 'ok';
  end if;
  update public.players
  set failed_attempts = player.failed_attempts + 1,
      locked_until = case when player.failed_attempts + 1 >= 5 then now() + interval '1 minute' end
  where name = player.name;
  return 'wrong';
end;
$$;


revoke execute on function player_exists(text), register_player(text, text),
  check_password(text, text) from public;
grant execute on function player_exists(text), register_player(text, text),
  check_password(text, text) to anon, authenticated;
