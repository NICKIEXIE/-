/**
 * 套件插件的离线冒烟测试（不碰任何 DSH profile）。
 *
 * 用假 ctx 导入 plugin/index.mjs，抓住注册的 provider，然后：
 *   1. 按注册表 validateCandidate 的规则校验每个候选（名称文法、非空描述、
 *      布尔 invocation、provider 名一致、数值 rank、source 是字符串）
 *   2. 校验 get() 返回的定义与候选同名、正文非空
 *   3. **校验关键不变式**：<resourceBase>/../knowledge 必须存在——这就是
 *      skill 正文里 `<skill-directory>/../knowledge/…` 能解析的前提
 *
 * 用法：node plugin-smoke.mjs <套件根目录>
 */
import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { pathToFileURL } from 'node:url'

const suite = path.resolve(process.argv[2] ?? '.')
const plugin = await import(pathToFileURL(path.join(suite, 'plugin', 'index.mjs')).href)

const NAME_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const warnings = []
let captured

const ctx = {
  logger: { warn: (message) => warnings.push(message) },
  skills: {
    registerProvider(factory) {
      captured = factory({ invalidate() {} })
    },
  },
}

plugin.apply(ctx)
assert.ok(captured, 'plugin 没有调用 ctx.skills.registerProvider')

const candidates = await captured.list()
assert.ok(candidates.length > 0, 'list() 没有返回任何候选')

for (const candidate of candidates) {
  // 镜像 @deepseek-ai/dsh-skill 的 validateCandidate()
  assert.ok(NAME_RE.test(candidate.name), `名称不合法: ${candidate.name}`)
  assert.equal(typeof candidate.description, 'string')
  assert.ok(candidate.description.length > 0, `description 为空: ${candidate.name}`)
  assert.equal(typeof candidate.invocation.modelInvocable, 'boolean')
  assert.equal(typeof candidate.invocation.userInvocable, 'boolean')
  if (candidate.whenToUse !== undefined) assert.equal(typeof candidate.whenToUse, 'string')
  assert.equal(typeof candidate.source, 'string')
  assert.ok(Number.isFinite(candidate.rank), `rank 不是数字: ${candidate.name}`)
  assert.equal(candidate.provider, captured.name, 'provider 必须等于 provider 名')
  assert.equal(candidate.resourceBase.kind, 'directory')

  const definition = await captured.get(candidate, {})
  assert.equal(definition.name, candidate.name, 'get() 的名称必须与候选一致')
  assert.ok(definition.content.length > 0, `正文为空: ${candidate.name}`)

  // 关键不变式：正文里的 `<skill-directory>/../knowledge/…` 与 `../scripts/…`
  const knowledge = path.resolve(candidate.resourceBase.path, '..', 'knowledge')
  const scripts = path.resolve(candidate.resourceBase.path, '..', 'scripts')
  assert.ok(existsSync(knowledge), `${candidate.name}: ${knowledge} 不存在 → 知识库引用会断链`)
  assert.ok(existsSync(scripts), `${candidate.name}: ${scripts} 不存在 → 脚本引用会断链`)

  console.log(
    `[ OK ] ${candidate.name.padEnd(22)} rank=${candidate.rank}  desc=${String(candidate.description.length).padStart(3)}字符  body=${String(definition.content.length).padStart(5)}字符  base=…/${path.basename(candidate.resourceBase.path)}`,
  )
}

assert.deepEqual(warnings, [], `插件发出警告: ${warnings.join(' | ')}`)
console.log(`\nprovider="${captured.name}"  ${candidates.length} 个候选全部通过注册表级校验，resourceBase 不变式成立`)
