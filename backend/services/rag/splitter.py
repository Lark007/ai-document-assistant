# 切片，按字符切，默认每块 500 字，重叠 80 字。可以根据需要调整 chunk_size 和 overlap。
def split_text_length(text: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
    """按固定长度滑动窗口切块。overlap 让相邻块共享一部分内容，避免答案被切断。"""
    text = text.strip()
    if not text:
        return []
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap 必须满足 0 <= overlap < chunk_size")

    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = end - overlap
    return chunks

# 切片，按照回车符切割
def split_text_line(text: str, max_chunk_size: int = 800, overlap: int = 80) -> list[str]:
    """按回车符切块。"""
    text = text.strip()
    if not text or max_chunk_size <= 0:
        return []

    if "\n\n" in text:
        paragraphs = text.split("\n\n")
    else:
        paragraphs = text.split("\n")

    chunks = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # 如果单个段落本身就超过了 max_chunk_size，必须强行切分
        if len(para) > max_chunk_size:
            sub_chunks = split_text_length(para, max_chunk_size, overlap)
            chunks.extend(sub_chunks)
            continue

        chunks.append(para)

    return chunks



