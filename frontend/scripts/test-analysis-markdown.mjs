// scripts/test-analysis-markdown.mjs
// 纯函数离线测试：不依赖 vitest/jest，node 直接运行。
// 运行：node scripts/test-analysis-markdown.mjs

import { formatAnalysisMarkdown } from '../src/utils/analysisMarkdown.js'

let passed = 0
let failed = 0

function check(name, condition) {
  if (condition) {
    passed++
    console.log(`  ✓ ${name}`)
  } else {
    failed++
    console.log(`  ✗ ${name}`)
  }
}

const HEADINGS = ['## 摘要', '## 关键点', '## 行动项', '## 关键词', '## 可以继续追问']

// 用例 1：字段齐全的正常结果
console.log('\n[用例 1] 字段齐全的正常结果')
const full = {
  summary: '本文介绍 FastAPI 的核心特性。',
  key_points: ['异步路由', 'Pydantic 校验'],
  keywords: ['FastAPI', 'Python'],
  action_items: ['完成上传接口'],
  questions: ['依赖注入怎么实现？'],
}
const mdFull = formatAnalysisMarkdown(full)
for (const h of HEADINGS) check(`包含标题 ${h}`, mdFull.includes(h))
check('摘要正文出现', mdFull.includes('本文介绍 FastAPI 的核心特性。'))
check('关键点条目出现', mdFull.includes('异步路由'))
check('关键词条目出现', mdFull.includes('FastAPI'))
check('行动项条目出现', mdFull.includes('完成上传接口'))
check('追问条目出现', mdFull.includes('依赖注入怎么实现？'))

// 用例 2：空对象，缺失字段走兜底
console.log('\n[用例 2] 空对象 {}')
const mdEmpty = formatAnalysisMarkdown({})
for (const h of HEADINGS) check(`包含标题 ${h}`, mdEmpty.includes(h))
check('摘要兜底：（暂无摘要）', mdEmpty.includes('（暂无摘要）'))
check('关键点兜底：暂无关键点', mdEmpty.includes('暂无关键点'))
check('行动项兜底：暂无行动项', mdEmpty.includes('暂无行动项'))
check('关键词兜底：暂无关键词', mdEmpty.includes('暂无关键词'))
check('追问兜底：暂无追问问题', mdEmpty.includes('暂无追问问题'))

// 用例 3：null 输入 + 字段类型错误，不崩溃
console.log('\n[用例 3] null 输入 + 字段类型错误')
let mdBad
try {
  mdBad = formatAnalysisMarkdown(null)
  check('null 输入未抛异常', true)
} catch (e) {
  check('null 输入未抛异常', false)
  mdBad = ''
}
const mdTypeError = formatAnalysisMarkdown({ key_points: '不是数组', keywords: 123 })
check('非数组字段未崩溃', typeof mdTypeError === 'string')
check('非数组关键点走兜底', mdTypeError.includes('暂无关键点'))
check('非数组关键词走兜底', mdTypeError.includes('暂无关键词'))

// 汇总
console.log(`\n结果：通过 ${passed} 条，失败 ${failed} 条`)
if (failed > 0) process.exit(1)
