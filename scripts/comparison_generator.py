#!/usr/bin/env python3
"""
论文降重 - 对比视图生成脚本
功能：生成原文与改写文本的逐句对比视图
"""

import re
import json
import sys
from typing import List, Dict, Tuple
from difflib import SequenceMatcher


class ComparisonGenerator:
    """对比视图生成器"""

    def __init__(self):
        self.comparisons = []

    def generate(
        self, original_text: str, rewritten_text: str
    ) -> Dict:
        """
        生成对比视图
        """
        result = {
            'comparisons': [],
            'statistics': {},
            'summary': {},
        }

        # 将文本分割为句子
        orig_sentences = self._split_sentences(original_text)
        rewr_sentences = self._split_sentences(rewritten_text)

        # 生成逐句对比
        comparisons = self._compare_sentences(orig_sentences, rewr_sentences)
        result['comparisons'] = comparisons

        # 生成统计信息
        result['statistics'] = self._generate_statistics(comparisons)

        # 生成摘要
        result['summary'] = self._generate_summary(
            original_text, rewritten_text, comparisons
        )

        return result

    def _split_sentences(self, text: str, language: str = 'zh') -> List[Dict]:
        """将文本分割为句子"""
        sentences = []

        if language == 'zh':
            # 中文句子分割
            pattern = r'[^。！？；]+[。！？；]?'
            matches = re.finditer(pattern, text)
            for i, match in enumerate(matches):
                sent = match.group().strip()
                if sent:
                    sentences.append({
                        'index': i,
                        'text': sent,
                        'start': match.start(),
                        'end': match.end(),
                    })
        else:
            # 英文句子分割
            pattern = r'[^.!?]+[.!?]?'
            matches = re.finditer(pattern, text)
            for i, match in enumerate(matches):
                sent = match.group().strip()
                if sent:
                    sentences.append({
                        'index': i,
                        'text': sent,
                        'start': match.start(),
                        'end': match.end(),
                    })

        return sentences

    def _compare_sentences(
        self, orig_sentences: List[Dict], rewr_sentences: List[Dict]
    ) -> List[Dict]:
        """对比句子并生成修改信息"""
        comparisons = []

        # 使用简单的对齐策略
        max_len = max(len(orig_sentences), len(rewr_sentences))

        for i in range(max_len):
            orig = orig_sentences[i] if i < len(orig_sentences) else None
            rewr = rewr_sentences[i] if i < len(rewr_sentences) else None

            comparison = self._analyze_sentence_pair(orig, rewr)
            comparisons.append(comparison)

        return comparisons

    def _analyze_sentence_pair(
        self, orig: Dict, rewr: Dict
    ) -> Dict:
        """分析句子对，确定修改类型"""
        if orig is None:
            return {
                'index': rewr['index'],
                'original': '',
                'rewritten': rewr['text'],
                'change_type': '新增',
                'similarity': 0,
                'position': f'第{rewr["index"]+1}句',
            }

        if rewr is None:
            return {
                'index': orig['index'],
                'original': orig['text'],
                'rewritten': '',
                'change_type': '删除',
                'similarity': 0,
                'position': f'第{orig["index"]+1}句',
            }

        # 计算相似度
        similarity = self._calculate_similarity(orig['text'], rewr['text'])

        # 确定修改类型
        if similarity >= 0.9:
            change_type = '未修改'
        elif similarity >= 0.7:
            change_type = '微调'
        elif similarity >= 0.5:
            change_type = '句式变换'
        elif similarity >= 0.3:
            change_type = '语义改写'
        else:
            change_type = '深度改写'

        return {
            'index': orig['index'],
            'original': orig['text'],
            'rewritten': rewr['text'],
            'change_type': change_type,
            'similarity': round(similarity, 3),
            'position': f'第{orig["index"]+1}句',
        }

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的相似度"""
        return SequenceMatcher(None, text1, text2).ratio()

    def _generate_statistics(self, comparisons: List[Dict]) -> Dict:
        """生成修改统计信息"""
        total = len(comparisons)
        type_counts = {}
        total_similarity = 0
        modified_count = 0

        for comp in comparisons:
            change_type = comp['change_type']
            type_counts[change_type] = type_counts.get(change_type, 0) + 1

            if change_type != '未修改':
                modified_count += 1

            total_similarity += comp['similarity']

        avg_similarity = total_similarity / max(total, 1)
        modification_rate = modified_count / max(total, 1)

        return {
            'total_sentences': total,
            'modified_sentences': modified_count,
            'modification_rate': round(modification_rate * 100, 1),
            'average_similarity': round(avg_similarity, 3),
            'change_type_distribution': type_counts,
        }

    def _generate_summary(
        self, original: str, rewritten: str, comparisons: List[Dict]
    ) -> Dict:
        """生成处理摘要"""
        orig_len = len(original)
        rewr_len = len(rewritten)
        change_pct = ((rewr_len - orig_len) / max(orig_len, 1)) * 100

        # 找出改动最大的句子
        sorted_by_change = sorted(
            [c for c in comparisons if c['change_type'] != '未修改'],
            key=lambda x: x['similarity']
        )

        most_changed = sorted_by_change[:3] if sorted_by_change else []

        return {
            'original_length': orig_len,
            'rewritten_length': rewr_len,
            'length_change_percent': round(change_pct, 1),
            'most_changed_sentences': [
                {
                    'position': c['position'],
                    'original': c['original'][:50] + '...' if len(c['original']) > 50 else c['original'],
                    'rewritten': c['rewritten'][:50] + '...' if len(c['rewritten']) > 50 else c['rewritten'],
                    'similarity': c['similarity'],
                }
                for c in most_changed
            ],
        }

    def generate_html(self, comparisons: List[Dict], statistics: Dict) -> str:
        """生成 HTML 格式的对比视图"""
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>论文降重对比视图</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { color: #333; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
        .stat-card { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #4a90d9; }
        .stat-label { font-size: 12px; color: #666; text-transform: uppercase; }
        .stat-value { font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th { background: #4a90d9; color: white; padding: 12px; text-align: left; font-weight: 500; }
        td { padding: 12px; border-bottom: 1px solid #eee; vertical-align: top; }
        tr:hover { background: #f8f9fa; }
        .original { color: #666; background: #fff5f5; }
        .rewritten { color: #333; background: #f5fff5; }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 12px; font-weight: 500; }
        .badge-未修改 { background: #e8f5e9; color: #2e7d32; }
        .badge-微调 { background: #fff3e0; color: #ef6c00; }
        .badge-句式变换 { background: #e3f2fd; color: #1565c0; }
        .badge-语义改写 { background: #fce4ec; color: #c2185b; }
        .badge-深度改写 { background: #f3e5f5; color: #7b1fa2; }
        .similarity { font-size: 12px; color: #999; }
    </style>
</head>
<body>
    <div class="container">
        <h1>论文降重对比视图</h1>
"""

        # 添加统计信息
        html += f"""
        <div class="stats">
            <div class="stat-card">
                <div class="stat-label">总句子数</div>
                <div class="stat-value">{statistics['total_sentences']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">修改句子数</div>
                <div class="stat-value">{statistics['modified_sentences']}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">修改比例</div>
                <div class="stat-value">{statistics['modification_rate']}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">平均相似度</div>
                <div class="stat-value">{statistics['average_similarity']:.1%}</div>
            </div>
        </div>
"""

        # 添加对比表格
        html += """
        <table>
            <thead>
                <tr>
                    <th style="width: 5%;">序号</th>
                    <th style="width: 42%;">原文</th>
                    <th style="width: 42%;">改写后</th>
                    <th style="width: 11%;">修改类型</th>
                </tr>
            </thead>
            <tbody>
"""

        for comp in comparisons:
            badge_class = f"badge-{comp['change_type']}"
            html += f"""
                <tr>
                    <td>{comp['index'] + 1}</td>
                    <td class="original">{comp['original']}</td>
                    <td class="rewritten">{comp['rewritten']}</td>
                    <td>
                        <span class="badge {badge_class}">{comp['change_type']}</span>
                        <div class="similarity">相似度: {comp['similarity']:.1%}</div>
                    </td>
                </tr>
"""

        html += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

        return html


def main():
    """命令行入口"""
    if len(sys.argv) < 3:
        print("用法: python comparison_generator.py <原文文件> <改写文件> [输出HTML路径]")
        sys.exit(1)

    original_path = sys.argv[1]
    rewritten_path = sys.argv[2]
    output_path = sys.argv[3] if len(sys.argv) > 3 else 'comparison.html'

    try:
        with open(original_path, 'r', encoding='utf-8') as f:
            original = f.read()
        with open(rewritten_path, 'r', encoding='utf-8') as f:
            rewritten = f.read()
    except FileNotFoundError as e:
        print(f"错误：{e}")
        sys.exit(1)

    generator = ComparisonGenerator()
    result = generator.generate(original, rewritten)

    # 生成 HTML
    html = generator.generate_html(result['comparisons'], result['statistics'])

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"对比视图已保存到: {output_path}")
    print(f"\n===== 对比摘要 =====")
    print(f"总句子数: {result['statistics']['total_sentences']}")
    print(f"修改句子数: {result['statistics']['modified_sentences']}")
    print(f"修改比例: {result['statistics']['modification_rate']}%")
    print(f"平均相似度: {result['statistics']['average_similarity']:.1%}")
    print(f"\n修改类型分布:")
    for change_type, count in result['statistics']['change_type_distribution'].items():
        print(f"  - {change_type}: {count} 句")


if __name__ == '__main__':
    main()
