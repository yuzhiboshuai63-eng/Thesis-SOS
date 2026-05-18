#!/usr/bin/env python3
"""
论文降重 - 改写质量检查脚本
功能：验证改写后文本的语义完整性、学术规范性和降重效果
"""

import re
import json
import sys
from typing import List, Dict, Tuple, Optional


class QualityChecker:
    """改写质量检查器"""

    def __init__(self):
        self.issues = []

    def check(
        self, original_text: str, rewritten_text: str, mode: str = 'reduce-dup'
    ) -> Dict:
        """
        主检查函数
        mode: 'reduce-dup', 'reduce-ai', 'reduce-both', 'predict-ai'
        """
        self.issues = []
        result = {
            'mode': mode,
            'overall_score': 0,
            'checks': {},
            'issues': [],
            'suggestions': [],
        }

        # 基础检查（所有模式）
        result['checks']['length_comparison'] = self._check_length(
            original_text, rewritten_text
        )
        result['checks']['punctuation'] = self._check_punctuation(rewritten_text)
        result['checks']['completeness'] = self._check_completeness(
            original_text, rewritten_text
        )

        # 降重模式检查
        if mode in ('reduce-dup', 'reduce-both'):
            result['checks']['similarity'] = self._check_similarity(
                original_text, rewritten_text
            )
            result['checks']['consecutive_chars'] = self._check_consecutive_chars(
                original_text, rewritten_text
            )

        # 降AI率模式检查
        if mode in ('reduce-ai', 'reduce-both'):
            result['checks']['ai_patterns'] = self._check_ai_patterns(
                rewritten_text
            )
            result['checks']['sentence_variety'] = self._check_sentence_variety(
                rewritten_text
            )
            result['checks']['vocabulary_diversity'] = self._check_vocabulary_diversity(
                rewritten_text
            )

        # 汇总问题
        result['issues'] = self.issues
        result['suggestions'] = self._generate_suggestions(result)

        # 计算总分
        result['overall_score'] = self._calculate_score(result)

        return result

    def _check_length(
        self, original: str, rewritten: str
    ) -> Dict:
        """检查改写后文本长度变化"""
        orig_len = len(original)
        rewr_len = len(rewritten)
        ratio = rewr_len / max(orig_len, 1)
        change_pct = (rewr_len - orig_len) / max(orig_len, 1) * 100

        status = 'pass'
        if ratio < 0.7:
            status = 'warning'
            self.issues.append({
                'level': 'warning',
                'category': '长度变化',
                'message': f'改写后文本长度减少了{abs(change_pct):.1f}%，可能丢失了重要内容',
            })
        elif ratio > 1.5:
            status = 'warning'
            self.issues.append({
                'level': 'warning',
                'category': '长度变化',
                'message': f'改写后文本长度增加了{change_pct:.1f}%，可能添加了不必要的内容',
            })

        return {
            'status': status,
            'original_length': orig_len,
            'rewritten_length': rewr_len,
            'ratio': round(ratio, 3),
            'change_percent': round(change_pct, 1),
        }

    def _check_punctuation(self, text: str) -> Dict:
        """检查标点符号使用"""
        issues = []

        # 检查中文标点
        chinese_punct = '，。！？；：""''（）【】《》'
        english_punct = ',.!?;:\'"()[]<>'

        # 检查是否有中英文标点混用
        has_chinese = any(p in text for p in chinese_punct)
        has_english = any(p in text for p in english_punct)

        # 检查连续标点
        consecutive = re.findall(r'[。！？]{2,}', text)
        if consecutive:
            issues.append('存在连续句末标点')

        # 检查省略号格式
        bad_ellipsis = re.findall(r'\.{3,}', text)
        if bad_ellipsis:
            issues.append('英文省略号应改为中文省略号"……"')

        status = 'pass' if not issues else 'warning'
        if issues:
            self.issues.append({
                'level': 'warning',
                'category': '标点符号',
                'message': f'标点问题：{"; ".join(issues)}',
            })

        return {
            'status': status,
            'has_chinese_punct': has_chinese,
            'has_english_punct': has_english,
            'issues': issues,
        }

    def _check_completeness(
        self, original: str, rewritten: str
    ) -> Dict:
        """检查改写后文本的完整性"""
        issues = []

        # 检查数字是否保留
        orig_numbers = set(re.findall(r'\d+\.?\d*', original))
        rewr_numbers = set(re.findall(r'\d+\.?\d*', rewritten))
        missing_numbers = orig_numbers - rewr_numbers
        if missing_numbers and orig_numbers:
            issues.append(f'部分数字可能丢失或被修改：{list(missing_numbers)[:5]}')

        # 检查专有名词是否保留（简单的英文大写词检测）
        orig_terms = set(re.findall(r'[A-Z][a-zA-Z]+', original))
        rewr_terms = set(re.findall(r'[A-Z][a-zA-Z]+', rewritten))
        missing_terms = orig_terms - rewr_terms
        if missing_terms and orig_terms:
            issues.append(f'部分专有名词可能丢失：{list(missing_terms)[:5]}')

        status = 'pass' if not issues else 'warning'
        if issues:
            for issue in issues:
                self.issues.append({
                    'level': 'warning',
                    'category': '完整性',
                    'message': issue,
                })

        return {
            'status': status,
            'issues': issues,
        }

    def _check_similarity(
        self, original: str, rewritten: str
    ) -> Dict:
        """检查原文与改写文本的相似度（简单字符级）"""
        # 使用简单的字符重叠率作为相似度估算
        orig_chars = set(original)
        rewr_chars = set(rewritten)
        if not orig_chars:
            return {'status': 'pass', 'similarity': 0}

        overlap = orig_chars & rewr_chars
        char_similarity = len(overlap) / len(orig_chars)

        # 检查n-gram重叠（2-gram和3-gram）
        def get_ngrams(text, n):
            return set(text[i:i+n] for i in range(len(text)-n+1))

        bigram_overlap = len(get_ngrams(original, 2) & get_ngrams(rewritten, 2))
        trigram_overlap = len(get_ngrams(original, 3) & get_ngrams(rewritten, 3))

        total_bigrams = len(get_ngrams(original, 2))
        bigram_similarity = bigram_overlap / max(total_bigrams, 1)

        status = 'pass'
        if bigram_similarity > 0.6:
            status = 'warning'
            self.issues.append({
                'level': 'warning',
                'category': '相似度',
                'message': f'改写后与原文的2-gram相似度仍为{bigram_similarity:.1%}，建议进一步改写',
            })

        return {
            'status': status,
            'char_similarity': round(char_similarity, 3),
            'bigram_similarity': round(bigram_similarity, 3),
            'trigram_overlap': trigram_overlap,
        }

    def _check_consecutive_chars(
        self, original: str, rewritten: str, threshold: int = 13
    ) -> Dict:
        """检查是否存在连续相同字符（知网标准）"""
        max_consecutive = 0
        consecutive_segments = []

        # 查找原文中所有长度>=threshold的子串在改写文本中的出现
        for i in range(len(original) - threshold + 1):
            segment = original[i:i+threshold]
            if segment in rewritten:
                max_consecutive = max(max_consecutive, threshold)
                # 尝试找到更长的匹配
                j = threshold + 1
                while j <= len(original) - i:
                    longer = original[i:i+j]
                    if longer in rewritten:
                        max_consecutive = max(max_consecutive, j)
                        j += 1
                    else:
                        break
                if max_consecutive >= threshold:
                    consecutive_segments.append({
                        'text': original[i:i+max_consecutive],
                        'length': max_consecutive,
                    })

        # 去重
        seen = set()
        unique_segments = []
        for seg in consecutive_segments:
            if seg['text'] not in seen:
                seen.add(seg['text'])
                unique_segments.append(seg)

        status = 'pass' if not unique_segments else 'fail'
        if unique_segments:
            self.issues.append({
                'level': 'error',
                'category': '连续字符',
                'message': f'发现{len(unique_segments)}处连续相同字符（≥{threshold}字符），知网检测会标红',
            })

        return {
            'status': status,
            'threshold': threshold,
            'max_consecutive': max_consecutive,
            'violations': unique_segments[:10],  # 最多显示10个
            'violation_count': len(unique_segments),
        }

    def _check_ai_patterns(self, text: str) -> Dict:
        """检查AI文本特征模式"""
        ai_indicators = []

        # AI高频词检测
        ai_words = [
            '深入', '全面', '有效', '充分利用', '具有重要意义',
            '发挥着重要作用', '不可或缺', '日益', '不断', '显著',
        ]
        found_ai_words = [w for w in ai_words if w in text]
        if found_ai_words:
            ai_indicators.append(f'发现AI高频词：{", ".join(found_ai_words)}')

        # AI句式模式检测
        ai_patterns = [
            (r'随着.+?的(?:发展|进步|普及|提升)', 'AI典型句式"随着...的发展"'),
            (r'首先.*?其次.*?最后', 'AI列举模式"首先...其次...最后"'),
            (r'综上所述', 'AI总结词"综上所述"'),
            (r'值得注意的是', 'AI过渡词"值得注意的是"'),
        ]
        for pattern, desc in ai_patterns:
            if re.search(pattern, text):
                ai_indicators.append(desc)

        # 句子长度均匀性检测
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
        if sentences:
            lengths = [len(s) for s in sentences]
            avg_len = sum(lengths) / len(lengths)
            variance = sum((l - avg_len) ** 2 for l in lengths) / len(lengths)
            std_dev = variance ** 0.5

            if std_dev < 8:
                ai_indicators.append(
                    f'句子长度过于均匀（标准差{std_dev:.1f}字符），缺乏自然变化'
                )

        status = 'pass' if len(ai_indicators) <= 2 else 'warning'
        if ai_indicators:
            self.issues.append({
                'level': 'info' if len(ai_indicators) <= 2 else 'warning',
                'category': 'AI特征',
                'message': f'AI特征指标（{len(ai_indicators)}项）：{"; ".join(ai_indicators[:5])}',
            })

        return {
            'status': status,
            'indicator_count': len(ai_indicators),
            'indicators': ai_indicators,
        }

    def _check_sentence_variety(self, text: str) -> Dict:
        """检查句子多样性"""
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 5]

        if not sentences:
            return {'status': 'pass', 'variety_score': 0}

        lengths = [len(s) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        std_dev = (sum((l - avg_len) ** 2 for l in lengths) / len(lengths)) ** 0.5

        # 计算多样性得分（0-100）
        variety_score = min(100, std_dev * 5)

        # 检查句式类型
        has_short = any(l < 15 for l in lengths)
        has_long = any(l > 35 for l in lengths)
        has_question = any('？' in s for s in sentences)

        status = 'pass' if variety_score > 40 else 'warning'
        if variety_score <= 40:
            self.issues.append({
                'level': 'warning',
                'category': '句式多样性',
                'message': f'句子多样性不足（得分{variety_score:.0f}/100），建议增加长短句变化',
            })

        return {
            'status': status,
            'variety_score': round(variety_score, 1),
            'avg_length': round(avg_len, 1),
            'std_dev': round(std_dev, 1),
            'has_short_sentences': has_short,
            'has_long_sentences': has_long,
            'has_questions': has_question,
        }

    def _check_vocabulary_diversity(self, text: str) -> Dict:
        """检查词汇多样性"""
        # 简单的TTR（Type-Token Ratio）计算
        chars = [c for c in text if '\u4e00' <= c <= '\u9fff']  # 仅中文字符
        if not chars:
            return {'status': 'pass', 'ttr': 0}

        unique_chars = set(chars)
        ttr = len(unique_chars) / len(chars)

        status = 'pass' if ttr > 0.3 else 'warning'
        if ttr <= 0.3:
            self.issues.append({
                'level': 'warning',
                'category': '词汇多样性',
                'message': f'词汇多样性较低（TTR={ttr:.3f}），建议使用更多样的表达方式',
            })

        return {
            'status': status,
            'ttr': round(ttr, 3),
            'total_chars': len(chars),
            'unique_chars': len(unique_chars),
        }

    def _generate_suggestions(self, result: Dict) -> List[str]:
        """生成改进建议"""
        suggestions = []
        checks = result.get('checks', {})

        if 'similarity' in checks and checks['similarity']['status'] != 'pass':
            suggestions.append(
                '建议对相似度较高的段落进行深度语义改写，而非仅替换同义词'
            )

        if 'consecutive_chars' in checks and checks['consecutive_chars']['status'] != 'pass':
            suggestions.append(
                f'发现{checks["consecutive_chars"]["violation_count"]}处连续相同字符，'
                '建议对这些位置进行重点改写'
            )

        if 'ai_patterns' in checks and checks['ai_patterns']['status'] != 'pass':
            suggestions.append(
                '建议替换AI高频词汇，打破AI句式模式，增加个人化表达'
            )

        if 'sentence_variety' in checks and checks['sentence_variety']['status'] != 'pass':
            suggestions.append(
                '建议制造句长波动，增加短句和长句的交替使用'
            )

        if 'vocabulary_diversity' in checks and checks['vocabulary_diversity']['status'] != 'pass':
            suggestions.append(
                '建议使用更多样的词汇表达，避免重复使用相同的措辞'
            )

        if not suggestions:
            suggestions.append('改写质量良好，未发现明显问题。')

        return suggestions

    def _calculate_score(self, result: Dict) -> int:
        """计算总分（0-100）"""
        checks = result.get('checks', {})
        total = 0
        count = 0

        for name, check in checks.items():
            if isinstance(check, dict) and 'status' in check:
                if check['status'] == 'pass':
                    total += 100
                elif check['status'] == 'warning':
                    total += 60
                elif check['status'] == 'fail':
                    total += 20
                count += 1

        return round(total / max(count, 1))


def main():
    """命令行入口"""
    if len(sys.argv) < 3:
        print("用法: python quality_checker.py <原文文件> <改写文件> [模式] [输出JSON路径]")
        print("模式: reduce-dup | reduce-ai | reduce-both | predict-ai")
        sys.exit(1)

    original_path = sys.argv[1]
    rewritten_path = sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'reduce-dup'
    output_path = sys.argv[4] if len(sys.argv) > 4 else None

    try:
        with open(original_path, 'r', encoding='utf-8') as f:
            original = f.read()
        with open(rewritten_path, 'r', encoding='utf-8') as f:
            rewritten = f.read()
    except FileNotFoundError as e:
        print(f"错误：{e}")
        sys.exit(1)

    checker = QualityChecker()
    result = checker.check(original, rewritten, mode)

    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"质量检查结果已保存到: {output_path}")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    # 打印摘要
    print(f"\n===== 质量检查摘要 =====")
    print(f"总分: {result['overall_score']}/100")
    print(f"问题数: {len(result['issues'])}")
    for issue in result['issues']:
        level_icon = {'error': '❌', 'warning': '⚠️', 'info': 'ℹ️'}.get(
            issue['level'], '•'
        )
        print(f"  {level_icon} [{issue['category']}] {issue['message']}")
    print(f"\n改进建议:")
    for i, suggestion in enumerate(result['suggestions'], 1):
        print(f"  {i}. {suggestion}")


if __name__ == '__main__':
    main()
