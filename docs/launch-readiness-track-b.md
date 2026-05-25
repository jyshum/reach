# Reach Track B Launch Readiness

## Local Code Status

- ES256 Supabase JWT verification is supported in `backend/auth.py`.
- HS256 remains as a legacy/test fallback through `SUPABASE_JWT_SECRET`.
- Backend `.env` loading is enabled from `backend/.env`.
- API auth tests mock `_decode_token`, which is the stable test seam after ES256/JWKS support.
- Pipeline tests reflect the current founder/logo fields.
- Live YC/Algolia integration tests are opt-in with `RUN_INTEGRATION_TESTS=1`.

## Supabase Branded Auth Emails

Configure this in the Supabase dashboard before inviting real users.

1. Go to `Authentication` -> `Emails` -> `SMTP Settings`.
2. Enable custom SMTP.
3. Use a sender on the product domain, for example `Reach <hello@your-domain.com>`.
4. Configure DNS for the sending domain:
   - SPF includes the SMTP provider.
   - DKIM records from the SMTP provider are published.
   - DMARC exists, starting with `p=none` is acceptable for launch.
5. Update Supabase email templates:
   - Confirm signup
   - Magic link, if enabled later
   - Password recovery
6. Send a test email from Supabase and confirm:
   - sender name is Reach
   - links use the production app URL
   - message does not mention Supabase branding

## Supabase Auth URL Settings

In `Authentication` -> `URL Configuration`:

- Site URL: production frontend URL.
- Redirect URLs:
  - production frontend URL
  - production frontend `/login`
  - production frontend `/onboard`
  - localhost dev URL if local auth testing is still needed

## Backend Deployment

Railway/Render environment variables:

- `SUPABASE_URL`
- `SUPABASE_KEY`
- `SUPABASE_JWT_SECRET`

Backend checks after deploy:

- `GET /companies?limit=1` returns `200`.
- `GET /me` without auth returns `401`.
- Authenticated `GET /me` returns the current user profile.
- CORS allows the production frontend domain.

## Frontend Deployment

Vercel environment variables:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_API_URL` set to the production backend URL.

Frontend checks after deploy:

- Landing page loads founder preview cards.
- Signup redirects to onboarding.
- Feed requires auth.
- Brief page enforces the free brief limit.
- Email workspace can copy a draft.
- Mailto appears only when `founder_email` exists.

## Deferred

- Gmail OAuth sending and automatic reply tracking.
- Student social profiles.
- Stripe checkout.
- Backend search endpoint for complete paginated search.
