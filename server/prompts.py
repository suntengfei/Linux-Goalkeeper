import re

CHAT_SYSTEM_PROMPT = """你是一个Linux运维安全助手。你可以帮助用户：
1. 分析Shell命令的风险
2. 提供安全的操作建议
3. 解答Linux运维相关问题
4. 帮助用户避免危险操作

请用简洁、专业的语言回答用户问题。
"""

RISK_ANALYSIS_PROMPT = """你是一个Linux Shell安全分析专家。请分析给定的Shell命令和上下文，
从以下维度评估风险：

1. 命令本身的风险等级（danger/high/medium/low）
2. 可能影响的系统范围（文件系统、内核、进程、权限等）
3. 是否可以安全执行
4. 更安全的替代方案（如有）

请按以下格式输出：
风险等级: <danger/high/medium/low>
分析: <详细分析>
建议: <操作建议列表>
"""

def get_chat_system_prompt() -> str:
    return CHAT_SYSTEM_PROMPT

def get_risk_analysis_prompt() -> str:
    return RISK_ANALYSIS_PROMPT

# 高危命令特征：递归强制删除根/家目录、破坏文件系统、修改关键系统文件权限等。
# 使用正则描述特征而非完整命令字面量，避免工具自身被注入危险命令文本。
DANGER_PATTERNS = [
    r"rm\s+(-[a-z]*r[a-z]*f[a-z]*|-[a-z]*f[a-z]*r[a-z]*)\s+(/|~|\$HOME)(\s|$|/(\s|$))",
    r"chmod\s+777\s+/(etc|usr|bin|sbin|var|boot|root)\b",
    r"mkfs(\.\w+)?\s+/dev/",
    r"dd\s+[^|]*of=/dev/(sd|nvme|hd|vd)",
    r":\(\)\s*\{.*\}\s*;\s*:",
    r">\s*/dev/(sd|nvme|hd|vd)",
    r"mv\s+\S+\s+/(boot|etc)\b",
]

# 高风险命令特征：大范围删除、强制终止进程、修改权限、关机重启、管道执行远程脚本等
HIGH_PATTERNS = [
    r"rm\s+(-[a-z]*r[a-z]*f[a-z]*|-[a-z]*f[a-z]*r[a-z]*)\s+\S",
    r"kill\s+(-9|-KILL)\b",
    r"\b(killall|pkill)\b",
    r"\b(shutdown|reboot|halt|poweroff|init\s+0)\b",
    r"chmod\s+777\b",
    r"(curl|wget)\s+[^|]*\|\s*(ba)?sh\b",
    r"su(root|do)\b.*-c",
]

# 中风险命令特征：删除/覆盖类关键词、清空文件等
MEDIUM_PATTERNS = [
    r"\b(delete|remove)\b",
    r"删除",
    r"mv\s+\S+\s+/dev/null",
    r"truncate\s+-s\s+0\b",
    r">\s*\S+",
]

def quick_risk_check(command: str) -> str:
    """对命令做快速本地风险分级：danger/high/medium/low"""
    if not command or not command.strip():
        return "low"

    text = command.strip()
    for pattern in DANGER_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "danger"
    for pattern in HIGH_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "high"
    for pattern in MEDIUM_PATTERNS:
        if re.search(pattern, text, flags=re.IGNORECASE):
            return "medium"
    return "low"
