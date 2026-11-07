// 作用：在分析页和问答页之间共享当前文档的基本信息。
// 只保存少量元数据，不引入 Pinia，便于直接理解状态如何流动。
import { ref } from 'vue'

const STORAGE_KEY = 'ai-document-assistant-current-document'

// 读取 sessionStorage 中保存的当前文档信息，如果没有或解析失败则返回 null
function readSavedDocument() {
  try {
    return JSON.parse(sessionStorage.getItem(STORAGE_KEY))
  } catch {
    return null
  }
}

// 当前文档的状态，初始值为 sessionStorage 中保存的文档信息
const currentDocument = ref(readSavedDocument())

export function useCurrentDocument() {

  // 设置当前文档，并将其保存到 sessionStorage 中
  function setCurrentDocument(document) {
    currentDocument.value = document
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(document))
  }

  // 清除当前文档，并从 sessionStorage 中移除保存的文档信息
  function clearCurrentDocument() {
    currentDocument.value = null
    sessionStorage.removeItem(STORAGE_KEY)
  }

  // 返回当前文档状态和操作函数，供组件使用
  return {
    currentDocument,
    setCurrentDocument,
    clearCurrentDocument,
  }
}
