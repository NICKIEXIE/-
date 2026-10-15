/**
 * Cordis host plugin for this skill suite.
 *
 * One job: expose this package's `skills/` directory as DSH skills. DSH discovers
 * skills one level deep under a fixed set of roots, and a path inside
 * `node_modules` is none of them — so shipping `skills/` in the package file list
 * puts the files on disk where nothing will ever look at them. Registering a
 * provider is what turns them into skills.
 *
 * Two shipped implementations were used as the shape reference:
 *   * `@deepseek-ai/dsh-skill-office` — one provider over bundled assets, with a
 *     per-skill `resourceBase` pointing at the skill's own directory.
 *   * `dsh-kimi-ppt` — `inject = ['skills']` plus a dependency-free frontmatter
 *     reader instead of pulling in `yaml`.
 *
 * Candidates must satisfy the registry's validation, which is why every candidate
 * carries `source`, `provider` (equal to this provider's name) and a numeric
 * `rank`; a missing `source` only fails later, on first load.
 */
import { existsSync, readFileSync } from 'node:fs'
import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

/**
 * Skill provider identity. `name` (the plugin identity) and `PACKAGE_NAME` are
 * independent, but the patch file resolves the module specifier by package name,
 * so keep them aligned with `package.json`.
 */
export const name = 'dsh-shortvideo-suite'
export const inject = ['skills']

const PACKAGE_NAME = 'dsh-shortvideo-suite'
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/** Documented default for `BUNDLED_SKILL_RANK` in `@deepseek-ai/dsh-skill`. */
const DEFAULT_BUNDLED_RANK = 600
let bundledRank = DEFAULT_BUNDLED_RANK
try {
  const registry = await import('@deepseek-ai/dsh-skill')
  if (typeof registry.BUNDLED_SKILL_RANK === 'number') bundledRank = registry.BUNDLED_SKILL_RANK
} catch {
  // Standalone install without the peer dependency: keep the documented default.
}

const NAME_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const TRUTHY = new Set(['true', 'yes', 'on', '1'])
const FALSY = new Set(['false', 'no', 'off', '0'])
const LEGACY_KEYS = ['modelInvocable', 'userInvocable', 'disableModelInvocation']

/** Read the subset of YAML frontmatter this suite's `SKILL.md` files may use. */
function readFrontmatter(source, locator) {
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/u.exec(source)
  if (match === null) throw new Error(`${locator} 缺少 YAML frontmatter（首行必须是 ---）`)
  const data = {}
  for (const line of match[1].split(/\r?\n/)) {
    if (!line.trim() || line.trimStart().startsWith('#')) continue
    if (line[0] === ' ' || line[0] === '\t') continue
    const kv = /^([A-Za-z0-9_][A-Za-z0-9_-]*):[ \t]*(.*)$/u.exec(line)
    if (kv === null) continue
    let value = kv[2].trim()
    if (value.length >= 2 && value[0] === value[value.length - 1] && (value[0] === '"' || value[0] === "'")) {
      value = value.slice(1, -1)
    }
    data[kv[1]] = value
  }
  return { data, body: source.slice(match[0].length) }
}

function booleanField(data, key) {
  if (!Object.hasOwn(data, key) || data[key] === '') return undefined
  const value = String(data[key]).trim().toLowerCase()
  if (TRUTHY.has(value)) return true
  if (FALSY.has(value)) return false
  throw new Error(`frontmatter 字段 ${key} 必须是布尔值，当前是 ${JSON.stringify(data[key])}`)
}

/** Parse one `SKILL.md` into the candidate/definition shape the registry expects. */
function parseSkill(source, locator) {
  const { data, body } = readFrontmatter(source, locator)
  for (const legacy of LEGACY_KEYS) {
    if (Object.hasOwn(data, legacy)) {
      throw new Error(`frontmatter 字段 ${legacy} 已废弃，请改用 disable-model-invocation / user-invocable`)
    }
  }
  const skillName = data.name
  if (typeof skillName !== 'string' || !NAME_RE.test(skillName)) {
    throw new Error(`frontmatter 的 name 缺失或不是 kebab-case：${JSON.stringify(data.name)}`)
  }
  if (typeof data.description !== 'string' || data.description.length === 0) {
    throw new Error(`frontmatter 缺少 description：${locator}`)
  }
  return {
    name: skillName,
    description: data.description,
    ...(typeof data.whenToUse === 'string' && data.whenToUse.length > 0 ? { whenToUse: data.whenToUse } : {}),
    invocation: {
      modelInvocable: booleanField(data, 'disable-model-invocation') !== true,
      userInvocable: booleanField(data, 'user-invocable') !== false,
    },
    content: body.trim(),
  }
}

function apply(ctx) {
  const providerName = PACKAGE_NAME
  const provider = {
    name: providerName,
    async list() {
      let entries
      try {
        entries = await readdir(ROOT, { withFileTypes: true })
      } catch (error) {
        ctx.logger?.warn?.(`[${PACKAGE_NAME}] 读不到 ${ROOT}：${error.message}`)
        return []
      }
      const candidates = []
      // Layout: every skill is a direct child directory of the package root that
      // contains SKILL.md — identical to the layout install.py deploys, so the
      // `<skill-directory>/../knowledge/...` paths written in the bodies resolve
      // the same way in development, in a flat install, and under this plugin.
      for (const entry of entries.sort((left, right) => left.name.localeCompare(right.name))) {
        if (!entry.isDirectory()) continue
        const directory = path.join(ROOT, entry.name)
        const locator = path.join(directory, 'SKILL.md')
        if (!existsSync(locator)) continue
        try {
          const parsed = parseSkill(readFileSync(locator, 'utf8'), locator)
          candidates.push({
            name: parsed.name,
            description: parsed.description,
            ...(parsed.whenToUse === undefined ? {} : { whenToUse: parsed.whenToUse }),
            invocation: parsed.invocation,
            source: 'bundled',
            provider: providerName,
            rank: bundledRank,
            resourceBase: { kind: 'directory', path: directory },
            locator,
            path: locator,
          })
        } catch (error) {
          // Skip the broken skill instead of failing the whole plugin tree.
          ctx.logger?.warn?.(`[${PACKAGE_NAME}] 跳过 ${locator}：${error.message}`)
        }
      }
      return candidates
    },
    async get(candidate, options) {
      const { rank: _rank, locator, ...summary } = candidate
      const source = await readFile(locator, { encoding: 'utf8', signal: options.signal })
      return { ...summary, content: parseSkill(source, locator).content }
    },
  }
  ctx.skills.registerProvider(() => provider)
}

export { apply, parseSkill }
