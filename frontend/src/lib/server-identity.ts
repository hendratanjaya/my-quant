/**
 * Long-lived, browser-scoped identifier. Kept separate from the JWT session
 * (`server-session.ts`) so their lifetimes are independent:
 *   - JWT session: ~8 hours, matches Stockbit's daily invalidation
 *   - Identity:    ~1 year, so the "user" concept survives JWT expiry
 *
 * Anonymous — we generate a UUID on first visit and stash it in an
 * httpOnly, signed, encrypted cookie. No login flow needed.
 */

import { randomUUID } from 'node:crypto'

import { useSession } from '@tanstack/react-start/server'

interface IdentityData {
  user_id?: string
}

const IDENTITY_COOKIE_NAME = 'user-identity'
// ~1 year in seconds
const IDENTITY_MAX_AGE = 60 * 60 * 24 * 365

const serverIdentity = async () =>
  useSession<IdentityData>({
    name: IDENTITY_COOKIE_NAME,
    password:
      process.env.SESSION_SECRET ??
      'dev-only-please-set-SESSION_SECRET-in-env',
    maxAge: IDENTITY_MAX_AGE,
    cookie: {
      httpOnly: true,
      secure: import.meta.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: IDENTITY_MAX_AGE,
    },
  })

/**
 * Read the current user_id, generating and persisting one if the cookie is
 * empty or missing. Safe to call from any server function — first call in a
 * fresh browser triggers a Set-Cookie on the response.
 */
export async function getOrCreateUserId(): Promise<string> {
  const identity = await serverIdentity()
  if (identity.data.user_id) return identity.data.user_id
  const user_id = randomUUID()
  await identity.update({ user_id })
  return user_id
}
