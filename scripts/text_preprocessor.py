#!/usr/bin/env python3
"""
论文降重 - 文本预处理脚本
功能：识别文本结构、标记不可修改区域、按段落/句子切分
"""

import re
import json
import sys
from typing import List, Dict, Tuple, Optional


class TextPreprocessor:
    """文本预处理器"""

    # 不可修改区域的正则模式
    PROTECTED_PATTERNS = {
        'formula': r'\$[^$]+\$',                          # 行内公式 $...$
        'formula_block': r'\$\$[\s\S]+?\$\$',             # 块级公式 $$...$$
        'citation': r'[""「」][^""「」]+[""「」]',        # 引用内容
        'reference': r'^\[\d+\].+',                       # 参考文献条目
        'number': r'\d+\.?\d*%?',                         # 数字和百分比
        'english_term': r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*',  # 英文专有名词
        'url': r'https?://\S+',                           # URL
        'email': r'\S+@\S+\.\S+',                         # 邮箱
    }

    # 段落类型判断关键词
    SECTION_KEYWORDS = [
        '摘要', 'abstract', '目录', '引言', '绪论', '第一章', '第二章', '第三章',
        '第四章', '第五章', '第六章', '第七章', '结论', '参考文献', '致谢', '附录',
        '研究背景', '研究方法', '实验结果', '讨论', '总结与展望',
        '1.', '2.', '3.', '4.', '5.', '一、', '二、', '三、', '四、', '五、',
    ]

    REFERENCE_KEYWORDS = ['参考文献', 'References', 'Bibliography', '引用文献']

    def __init__(self):
        self.protected_ranges = []  # 存储不可修改的文本范围

    def preprocess(self, text: str) -> Dict:
        """
        主预处理函数
        返回预处理结果字典
        """
        result = {
            'original_text': text,
            'original_length': len(text),
            'paragraphs': [],
            'statistics': {},
            'protected_items': [],
        }

        # Step 1: 识别不可修改区域
        protected = self._find_protected_regions(text)
        result['protected_items'] = protected

        # Step 2: 按段落切分
        paragraphs = self._split_paragraphs(text)
        result['paragraphs'] = paragraphs

        # Step 3: 对每个段落进行分析
        for i, para in enumerate(paragraphs):
            para['type'] = self._classify_paragraph(para['text'])
            para['sentences'] = self._split_sentences(para['text'])
            para['protected'] = self._check_paragraph_protection(
                para['text'], protected
            )
            para['modifiable_ratio'] = self._calculate_modifiable_ratio(
                para['text'], para['protected']
            )

        # Step 4: 统计信息
        result['statistics'] = self._generate_statistics(paragraphs, text)

        return result

    def _find_protected_regions(self, text: str) -> List[Dict]:
        """识别文本中不可修改的区域"""
        protected = []
        for name, pattern in self.PROTECTED_PATTERNS.items():
            for match in re.finditer(pattern, text):
                protected.append({
                    'type': name,
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(),
                })
        # 按位置排序
        protected.sort(key=lambda x: x['start'])
        return protected

    def _split_paragraphs(self, text: str) -> List[Dict]:
        """按段落切分文本"""
        raw_paragraphs = re.split(r'\n\s*\n', text.strip())
        paragraphs = []
        offset = 0
        for para_text in raw_paragraphs:
            para_text = para_text.strip()
            if not para_text:
                continue
            start = text.find(para_text, offset)
            paragraphs.append({
                'index': len(paragraphs),
                'text': para_text,
                'start': start,
                'end': start + len(para_text),
                'length': len(para_text),
            })
            offset = start + len(para_text)
        return paragraphs

    def _classify_paragraph(self, text: str) -> str:
        """判断段落类型"""
        clean_text = text.strip()

        # 参考文献段落
        for kw in self.REFERENCE_KEYWORDS:
            if clean_text.startswith(kw) or re.match(r'^\[\d+\]', clean_text):
                return 'reference'

        # 章节标题
        for kw in self.SECTION_KEYWORDS:
            if clean_text.startswith(kw) and len(clean_text) < 50:
                return 'heading'

        # 图表标题
        if re.match(r'^(图|表|Figure|Table)\s*\d+', clean_text):
            return 'figure_table'

        # 公式段落
        if clean_text.startswith('$') or clean_text.startswith('$$'):
            return 'formula'

        # 引用段落（整段引用）
        if (clean_text.startswith('"') or clean_text.startswith('"') or
            clean_text.startswith('「')):
            return 'citation'

        # 默认为正文
        return 'body'

    def _split_sentences(self, text: str) -> List[Dict]:
        """按句子切分段落"""
        # 中文句子分割（句号、问号、感叹号、分号）
        sentence_endings = r'([。！？；])'
        parts = re.split(sentence_endings, text)

        sentences = []
        current = ''
        for part in parts:
            if re.match(sentence_endings, part):
                current += part
                if current.strip():
                    sentences.append({
                        'text': current.strip(),
                        'length': len(current.strip()),
                    })
                current = ''
            else:
                current += part

        if current.strip():
            sentences.append({
                'text': current.strip(),
                'length': len(current.strip()),
            })

        return sentences

    def _check_paragraph_protection(
        self, para_text: str, protected: List[Dict]
    ) -> List[Dict]:
        """检查段落中受保护的区域"""
        para_protected = []
        para_start = None
        para_end = None

        # 找到段落在全文中的位置
        for p in protected:
            if p['text'] in para_text:
                para_protected.append(p)
        return para_protected

    def _calculate_modifiable_ratio(
        self, para_text: str, protected: List[Dict]
    ) -> float:
        """计算段落中可修改内容的比例"""
        if not para_text:
            return 0.0

        protected_length = sum(len(p['text']) for p in protected)
        modifiable = max(0, len(para_text) - protected_length)
        return round(modifiable / len(para_text) * 100, 1)

    def _generate_statistics(
        self, paragraphs: List[Dict], text: str
    ) -> Dict:
        """生成统计信息"""
        total_chars = len(text)
        total_paras = len(paragraphs)
        total_sentences = sum(len(p.get('sentences', [])) for p in paragraphs)

        type_counts = {}
        for p in paragraphs:
            t = p.get('type', 'body')
            type_counts[t] = type_counts.get(t, 0) + 1

        modifiable_paras = sum(
            1 for p in paragraphs
            if p.get('type') in ('body', 'heading')
        )

        return {
            'total_chars': total_chars,
            'total_paragraphs': total_paras,
            'total_sentences': total_sentences,
            'type_distribution': type_counts,
            'modifiable_paragraphs': modifiable_paras,
            'protected_paragraphs': total_paras - modifiable_paras,
            'avg_sentence_length': round(
                total_chars / max(total_sentences, 1), 1
            ),
        }


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print("用法: python text_preprocessor.py <输入文件路径> [输出JSON路径]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    # 读取输入文件
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            text = f.read()
    except FileNotFoundError:
        print(f"错误：文件 '{input_path}' 不存在")
        sys.exit(1)

    # 执行预处理
    preprocessor = TextPreprocessor()
    result = preprocessor.preprocess(text)

    # 输出结果
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"预处理结果已保存到: {output_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 打印摘要
    stats = result['statistics']
    print(f"\n===== 预处理摘要 =====")
    print(f"总字符数: {stats['total_chars']}")
    print(f"总段落数: {stats['total_paragraphs']}")
    print(f"总句子数: {stats['total_sentences']}")
    print(f"可修改段落: {stats['modifiable_paragraphs']}")
    print(f"受保护段落: {stats['protected_paragraphs']}")
    print(f"平均句长: {stats['avg_sentence_length']} 字符")
    print(f"段落类型分布: {stats['type_distribution']}")


if __name__ == '__main__':
    main()
