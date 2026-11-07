// 作用：调用当前文档问答接口。
// Day 15 接入 RAG 时，可以新增 knowledge.js，不必直接改这个接口。
import http from './http'

export function askDocumentQuestion(documentId, question) {
  return http.post('/qa/', {
    document_id: documentId,
    question,
  })
}
