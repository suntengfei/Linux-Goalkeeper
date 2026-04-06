import re

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
