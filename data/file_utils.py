from pathlib import Path
from typing import List, Dict


def write_md(name: str, content: Dict[str, List[Dict]], output_path: str):
    md_lines = [f"# {name}\n"]

    for symbol, sig_list in content.items():
        md_lines.append(f"## {symbol}\n")
        if not sig_list:
            md_lines.append("_No signals_\n")
            continue

        # 获取所有键（假设每个 sig 的 key 都一致）
        headers = list(sig_list[0].keys())
        # 表头
        md_lines.append("| " + " | ".join(headers) + " |")
        # 分隔行
        md_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

        # 表格内容
        for sig in sig_list:
            row = [str(sig.get(h, "")) for h in headers]
            md_lines.append("| " + " | ".join(row) + " |")

        md_lines.append("\n")  # 分隔不同 symbol

    md_content = "\n".join(md_lines)

    # 保存到文件
    output_path = Path(output_path)
    output_path.write_text(md_content, encoding="utf-8")
