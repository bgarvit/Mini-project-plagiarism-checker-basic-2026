-- Plagify original_documents schema + RLS
-- Run in Supabase SQL Editor after creating a project.

-- Private storage bucket (create via Dashboard → Storage → New bucket)
-- Name: original-documents
-- Public: OFF

CREATE TABLE IF NOT EXISTS public.original_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id TEXT NOT NULL,
  document_name TEXT NOT NULL,
  storage_path TEXT,
  extracted_text TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_original_documents_owner
  ON public.original_documents (owner_id);

ALTER TABLE public.original_documents ENABLE ROW LEVEL SECURITY;

-- Backend uses service_role key (bypasses RLS). Policies below protect anon/authenticated clients.

CREATE POLICY "Owners can select own originals"
  ON public.original_documents
  FOR SELECT
  USING (auth.uid()::text = owner_id);

CREATE POLICY "Owners can insert own originals"
  ON public.original_documents
  FOR INSERT
  WITH CHECK (auth.uid()::text = owner_id);

CREATE POLICY "Owners can update own originals"
  ON public.original_documents
  FOR UPDATE
  USING (auth.uid()::text = owner_id);

CREATE POLICY "Owners can delete own originals"
  ON public.original_documents
  FOR DELETE
  USING (auth.uid()::text = owner_id);

-- Note: This app stores owner_id as the local JWT user id (integer as text)
-- when not using Supabase Auth. Prefer service-role access from the Python backend
-- and never expose the service-role key to the browser.
