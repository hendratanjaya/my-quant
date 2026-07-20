import { fetchFundamental, type FundamentalReport } from '#/lib/api'

/**
 * Slash commands available in the chat input. Add new ones here and they
 * automatically appear in the slash menu.
 */

export type CommandResult =
  | { kind: 'fundamental'; report: FundamentalReport }
  | { kind: 'text'; content: string }
  | { kind: 'error'; content: string }

export interface SlashCommand {
  name: string
  description: string
  usage: string
  run: (args: string[]) => Promise<CommandResult>
}

export const COMMANDS: SlashCommand[] = [
  {
    name: 'fd',
    description: 'Fundamental snapshot for a ticker',
    usage: '/fd <ticker>',
    async run(args) {
      if (args.length === 0) {
        return { kind: 'error', content: 'Usage: `/fd <ticker>` — e.g. `/fd BBRI`' }
      }
      try {
        const report = await fetchFundamental(args[0])
        return { kind: 'fundamental', report }
      } catch (err) {
        return { kind: 'error', content: `Failed to fetch: ${(err as Error).message}` }
      }
    },
  },
  {
    name: 'help',
    description: 'Show available commands',
    usage: '/help',
    async run() {
      const lines = COMMANDS.map((c) => `**${c.usage}** — ${c.description}`).join('\n')
      return { kind: 'text', content: `Available commands:\n${lines}` }
    },
  },
]

export function isSlashInput(text: string): boolean {
  return text.trimStart().startsWith('/')
}

export function parseSlashInput(text: string): { command: string; args: string[] } {
  const trimmed = text.trim().slice(1) // drop leading '/'
  const parts = trimmed.split(/\s+/).filter(Boolean)
  return { command: parts[0] ?? '', args: parts.slice(1) }
}

export function findCommand(name: string): SlashCommand | undefined {
  return COMMANDS.find((c) => c.name === name.toLowerCase())
}

/** Filter commands by a query like "/f" → matches "fd". */
export function filterCommands(query: string): SlashCommand[] {
  const q = query.trim().replace(/^\//, '').toLowerCase()
  if (!q) return COMMANDS
  return COMMANDS.filter((c) => c.name.startsWith(q))
}
