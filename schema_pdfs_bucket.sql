-- In Supabase Storage: Bucket "pdfs" anlegen (nicht public)
INSERT INTO storage.buckets (id, name, public)
VALUES ('pdfs', 'pdfs', false)
ON CONFLICT (id) DO NOTHING;

-- Service Role darf alles
CREATE POLICY "Service role full access pdfs"
ON storage.objects FOR ALL TO service_role
USING (bucket_id = 'pdfs')
WITH CHECK (bucket_id = 'pdfs');
