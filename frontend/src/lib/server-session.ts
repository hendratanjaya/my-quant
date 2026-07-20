import { useSession } from '@tanstack/react-start/server'

interface SessionData {
  token?: string
}

const SESSION_NAME = 'user-session'

export const serverSession = async () => {
  return useSession<SessionData>({
    name: SESSION_NAME,
    password:
      process.env.SESSION_SECRET ??
      'dev-only-please-set-SESSION_SECRET-in-env',
    cookie: {
      httpOnly: true,
      secure: import.meta.env.NODE_ENV === 'production',
      sameSite: 'lax',
    },
  })
}
