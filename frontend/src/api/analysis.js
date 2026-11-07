// 作用：调用 AI 文档结构化分析接口。
// 当前只传 document_id，Prompt 与 DeepSeek 调用应由后端负责。
import http from './http'

// 发起一次新的结构化分析（后端会落库）
export function analyzeDocument(documentId, regenerate = false) {
  const config = regenerate ? { params: { regenerate: true } } : {}
  return http.post(
    '/analysis/document',
    {document_id: documentId},
    config,
  )
}

// 读取已经保存过的分析结果（Day 22 新增的查看功能）
// 后端返回的结构是：
//   { document_id, record_id, analysis_type, created_at, result: { 五个字段 } }
// 页面真正要渲染的内容都在 result 里面，所以这里一次性拆平：
//   result     → 给结果卡片用
//   created_at → 给「保存时间」用
//   record_id  → 调试时看一眼是哪条记录
// 这样调用方不用再写一遍 response.result。
export function getAnalysisRecord(documentId) {
  return http.get(`/analysis/document/${documentId}`).then((response) => ({
    result: response.result,
    createdAt: response.created_at,
    recordId: response.record_id,
  }))
}
