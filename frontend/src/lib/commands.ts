import { fetchFundamental, type FundamentalReport } from '#/lib/api'
import { dispatchScreen, openScreenStream } from '#/lib/agent-api'
import { getUserIdFn } from '#/lib/server-fns'

export type CommandResult =
  | { kind: 'fundamental'; report: FundamentalReport }
  | { kind: 'text'; content: string }
  | { kind: 'error'; content: string }

export interface SlashCommand {
  name: string
  description: string
  usage: string
  run: (args: string[], onProgress?: (content: string) => void) => Promise<CommandResult>
}

const VALID_SIGNALS = ['ketat', 'superketat', 'theone', 'kamehameha']

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
    name: 'screen',
    description: 'Screen all IDX tickers for CI signals',
    usage: '/screen <ketat|superketat|theone|kamehameha> [...]',
    async run(args, onProgress) {
      const signals = args.map((a) => a.toLowerCase()).filter((a) => VALID_SIGNALS.includes(a))
      if (signals.length === 0) {
        return {
          kind: 'error',
          content: `Specify at least one signal: ${VALID_SIGNALS.join(', ')}`,
        }
      }

      let taskId: string
      try {
        const res = await dispatchScreen(signals)
        taskId = res.task_id
      } catch (err) {
        return { kind: 'error', content: `Failed to start screener: ${(err as Error).message}` }
      }

      const { user_id: userId } = await getUserIdFn()

      const TABLE_HEADER = '| Ticker | Signal | Vol | Mom (5d) |\n|--------|--------|-----|----------|\n'

      function buildTable(rows: string[]): string {
        return TABLE_HEADER + rows.join('\n')
      }

      return new Promise<CommandResult>((resolve) => {
        const rows: string[] = []
        const es = openScreenStream(taskId, userId)

        es.onmessage = (e: MessageEvent) => {
          try {
            const envelope = JSON.parse(e.data as string) as { type: string; data: Record<string, unknown> }

            if (envelope.type === 'hit') {
              const d = envelope.data
              const sigs = (d.signals as string[]).join(', ')
              const vol = d.volume_ratio != null ? `${(d.volume_ratio as number).toFixed(2)}x` : '—'
              const mom = d.momentum_5d_pct != null
                ? `${(d.momentum_5d_pct as number) >= 0 ? '+' : ''}${(d.momentum_5d_pct as number).toFixed(2)}%`
                : '—'
              rows.push(`| [${d.ticker}](/${(d.ticker as string).toLowerCase()}) | ${sigs} | ${vol} | ${mom} |`)
              onProgress?.(
                `## Screener — ${signals.join(', ').toUpperCase()}\n\nScanning… ${rows.length} hit${rows.length === 1 ? '' : 's'} so far:\n\n${buildTable(rows)}`,
              )
            }

            if (envelope.type === 'done') {
              es.close()
              if (rows.length === 0) {
                resolve({ kind: 'text', content: 'No tickers matched the selected signals.' })
              } else {
                resolve({
                  kind: 'text',
                  content: `## Screener — ${signals.join(', ').toUpperCase()}\n\n${buildTable(rows)}\n\n*${rows.length} result${rows.length === 1 ? '' : 's'}*`,
                })
              }
            }

            if (envelope.type === 'error') {
              es.close()
              resolve({ kind: 'error', content: (envelope.data as { message: string }).message })
            }
          } catch {
            // ignore malformed events
          }
        }

        es.onerror = () => {
          es.close()
          resolve({ kind: 'error', content: 'Screener stream disconnected.' })
        }
      })
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
  const trimmed = text.trim().slice(1)
  const parts = trimmed.split(/\s+/).filter(Boolean)
  return { command: parts[0] ?? '', args: parts.slice(1) }
}

export function findCommand(name: string): SlashCommand | undefined {
  return COMMANDS.find((c) => c.name === name.toLowerCase())
}

export function filterCommands(query: string): SlashCommand[] {
  const q = query.trim().replace(/^\//, '').toLowerCase()
  if (!q) return COMMANDS
  return COMMANDS.filter((c) => c.name.startsWith(q))
}
