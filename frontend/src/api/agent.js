// 调用Agent接口
import http from './http';

export function runAgent(question) {
  return http.post("/agent", { question });
}