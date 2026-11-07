// 作用：文档管理页用到的接口（列表 + 建立索引 + 删除）。
// 列表/删除在后端 api/documents.py，建索引在 api/qa.py，这里只是统一收口。
import http from './http'

// 取全部文档，带索引状态
export function listDocuments() {
  return http.get('/documents')
}

// 给某份文档建立（或重建）索引
export function indexDocument(documentId) {
  return http.post(`/qa/index/${documentId}`)
}

// 删除一份文档（连同它的分析记录和索引片段）
export function deleteDocument(documentId) {
  return http.delete(`/documents/${documentId}`)
}
