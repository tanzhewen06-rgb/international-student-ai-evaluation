from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REVISION = 'V4.13'

def revised_prompt(original):
    text = Path(original).read_bytes().decode('utf-8-sig')
    start = text.index('## V4.12: Grounding and Evaluator Self-Checks')
    end = text.index('## Compact Audit and Strict Score Computation', start)
    text = text[:start] + text[end:]
    rules = (HERE / 'review_protocol.md').read_text(encoding='utf-8')
    role = text.index('## Role and Evidence')
    text = text[:role] + rules + '\n\n' + text[role:]
    text = text.replace('# Evaluation Agent Prompt - V4.12', '# Evaluation Agent Prompt - V4.13', 1)
    text = re.sub(r'Keep one brief sentence of comment per dimension, preferably in Chinese; at most about 30 English words or 60 Chinese characters\.',
                  'Keep one brief sentence of comment per dimension, in English, with at most about 30 words.', text)
    if 'preferably in Chinese' in text:
        raise ValueError('The old output-language instruction remains.')
    return text
