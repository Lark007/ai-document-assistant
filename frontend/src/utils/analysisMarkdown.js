// 纯函数：把后端返回的结构化分析结果转成 Markdown 字符串。
// 约束：不读 DOM、不发请求、不触发下载；任何字段缺失/类型错误都容错，不抛异常。

// 将数组转换为 Markdown 列表
function toList(items, emptyText) {
  if (!Array.isArray(items)) return `- ${emptyText}\n`
  const valid = items.filter((x) => x != null && String(x).trim() !== '')
  if (!valid.length) return `- ${emptyText}\n`
  return valid.map((x) => `- ${String(x).trim()}\n`).join('')
}

export function formatAnalysisMarkdown(result) {
  const r = result || {}
  const summary =
    typeof r.summary === 'string' && r.summary.trim()
      ? r.summary.trim()
      : '（暂无摘要）'

  return [
    '# AI 结构化分析',
    '',
    '## 摘要',
    summary,
    '',
    '## 关键点',
    toList(r.key_points, '暂无关键点'),
    '## 行动项',
    toList(r.action_items, '暂无行动项'),
    '## 关键词',
    toList(r.keywords, '暂无关键词'),
    '## 可以继续追问',
    toList(r.questions, '暂无追问问题'),
  ].join('\n')
}
