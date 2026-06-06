-- Aktiv-Flag für Optionen
ALTER TABLE options ADD COLUMN IF NOT EXISTS active boolean DEFAULT true;

-- Vorlagen-Tabelle
CREATE TABLE IF NOT EXISTS templates (
  id         text primary key,
  name       text not null,
  option_ids jsonb default '[]'::jsonb,
  created_at timestamptz default now()
);
