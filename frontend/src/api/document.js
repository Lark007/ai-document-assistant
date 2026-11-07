// 作用：集中管理文档上传和文档详情接口。
// FastAPI 接收上传文件时，字段名需要与这里的 file 保持一致。
import http from './http'

// 作用：上传文档，返回文档的元数据和内容预览。
export function uploadDocument(file) {
  const formData = new FormData()
  formData.append('file', file)

  return http.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 作用：获取文档详情，包含文档内容和元数据。
export function getDocument(documentId) {
  return http.get(`/documents/${documentId}`)
}

// 作用：根据文档id获取文档名称。
export function getDocumentName(documentId) {
  return http.get(`/documents/name/${documentId}`)
}
