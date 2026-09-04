import re
from typing import List

SENSITIVE_PATTERNS = [
    (r'password\s*=\s*\S+', 'password=***'),
    (r'passwd\s*=\s*\S+', 'passwd=***'),
    (r'pwd\s*=\s*\S+', 'pwd=***'),
    (r'secret\s*=\s*\S+', 'secret=***'),
    (r'token\s*=\s*\S+', 'token=***'),
    (r'api_key\s*=\s*\S+', 'api_key=***'),
    (r'apikey\s*=\s*\S+', 'apikey=***'),
    (r'auth\s*=\s*\S+', 'auth=***'),
    (r'Bearer\s+\S+', 'Bearer ***'),
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-***'),
    (r'-----BEGIN\s+.*PRIVATE\s+KEY-----[\s\S]*?-----END\s+.*PRIVATE\s+KEY-----', '***PRIVATE KEY***'),
]

def mask_sensitive_data(text: str) -> str:
    if not text:
        return text

    masked_text = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        masked_text = re.sub(pattern, replacement, masked_text, flags=re.IGNORECASE)

    return masked_text

def prepare_for_llm(command: str, output: str, max_length: int = 1000,
                    head_length: int = 400, tail_length: int = 400) -> str:
    """将命令与输出整理为送入LLM的文本：先脱敏，超长时保留首尾并标注省略"""
    content = mask_sensitive_data(f"$ {command}\n{output}" if command else output)

    if len(content) <= max_length:
        return content

    omitted = len(content) - head_length - tail_length
    if omitted <= 0:
        return content

    return (
        content[:head_length]
        + f"\n...(中间省略 {omitted} 字符)...\n"
        + content[-tail_length:]
    )

KEY_INFO_MARKERS = (
    "error", "failed", "failure", "fatal", "critical",
    "denied", "permission", "warning", "exception", "timeout",
)

def extract_key_info(output: str) -> List[str]:
    """提取输出中包含错误/告警等关键信息的行"""
    if not output:
        return []

    lines = [line.strip() for line in output.splitlines() if line.strip()]
    key_lines = [
        line for line in lines
        if any(marker in line.lower() for marker in KEY_INFO_MARKERS)
    ]
    return key_lines if key_lines else lines[:5]
