#!/usr/bin/env python3
"""
同伴互评数据集导出脚本
将模拟生成的数据导出为标准格式，并使用大模型进行标签标注

输出格式:
[
  {
    "question": "作业题目/要求",
    "answer": "学生作品内容",
    "peer_review": "同伴评价内容",
    "ground_truth_label": "标签类别"
  },
  ...
]

ground_truth_label 共8个类别:
1. 支持 - 表达对作品的认可和肯定
2. 反对 - 表达对作品的否定或批评
3. 提问 - 提出疑问，寻求澄清
4. 澄清 - 解释或说明某些内容
5. 延伸 - 在原有基础上进行扩展或补充
6. 建议 - 提供改进意见或建议
7. 感谢 - 表达感谢或鼓励
8. 其他 - 不属于以上类别的内容
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import openai
from config.settings import Config

# 标签类别定义（8类评价标准）
LABEL_CATEGORIES = [
    "支持",       # 情感态度 - 简单的正面表达
    "反对",       # 情感态度 - 简单的负面表达
    "直接修正",   # 认知贡献 - 直接指出错误
    "不入观点",   # 认知贡献 - 知识陈述但无具体建议
    "指导建议",   # 认知贡献 - 具体改进建议
    "反思评估",   # 元认知 - 批判性反思
    "内化迁移",   # 元认知 - 学习借鉴他人思路
    "无关评语"    # 质量控制 - 与作品无关
]

LABEL_DESCRIPTIONS = {
    "支持": "少量文字的简单表达，通常表现为'学习了'、'很厉害'、'报告写的很好'等正面情感表达",
    "反对": "表达的是负面情绪，如'我觉得做的不太好'、'不够好'等简单的负面评价",
    "直接修正": "直接指出作品的错误，如'这个题的答案不是XX'、'这个代码的运行结果不正确'",
    "不入观点": "包含知识的呈现及对知识的一般性陈述，而非对具体建议的修改方向",
    "指导建议": "包含具体建议、概念或方法以改进作品，如'这个题用XX方式代入计算会更方便'",
    "反思评估": "评估中包含批判性反思，促进对经验的思考、指出作业中体现的知识、找到能展现的问题",
    "内化迁移": "从作品中看到了不一样的做题方法或思路，认为自己也可以学习这种思路",
    "无关评语": "与作品无关的评语，无实质内容"
}


class PeerReviewDatasetExporter:
    """同伴互评数据集导出器"""
    
    def __init__(self, use_llm_labeling: bool = True, batch_size: int = 10):
        """
        初始化导出器
        
        Args:
            use_llm_labeling: 是否使用大模型进行标签标注
            batch_size: 批量标注时每批的数量
        """
        self.use_llm_labeling = use_llm_labeling
        self.batch_size = batch_size
        
        if use_llm_labeling:
            self.client = openai.OpenAI(
                api_key=Config.OPENAI_API_KEY,
                base_url=Config.OPENAI_BASE_URL
            )
    
    def load_semester_data(self, semester_path: str) -> Dict[str, Any]:
        """
        加载学期数据
        
        Args:
            semester_path: 学期数据目录路径
            
        Returns:
            包含所有数据的字典
        """
        data = {}
        
        # 加载作业数据
        assignments_file = os.path.join(semester_path, "assignments.json")
        if os.path.exists(assignments_file):
            with open(assignments_file, 'r', encoding='utf-8') as f:
                data['assignments'] = {a['id']: a for a in json.load(f)}
        else:
            data['assignments'] = {}
        
        # 加载作品数据
        works_file = os.path.join(semester_path, "works.json")
        if os.path.exists(works_file):
            with open(works_file, 'r', encoding='utf-8') as f:
                data['works'] = {w['id']: w for w in json.load(f)}
        else:
            data['works'] = {}
        
        # 加载评估数据
        evaluations_file = os.path.join(semester_path, "evaluations.json")
        if os.path.exists(evaluations_file):
            with open(evaluations_file, 'r', encoding='utf-8') as f:
                data['evaluations'] = json.load(f)
        else:
            data['evaluations'] = []
        
        # 加载学生数据
        students_file = os.path.join(semester_path, "students.json")
        if os.path.exists(students_file):
            with open(students_file, 'r', encoding='utf-8') as f:
                data['students'] = {s['id']: s for s in json.load(f)}
        else:
            data['students'] = {}
        
        return data
    
    def extract_peer_review(self, evaluation: Dict[str, Any]) -> str:
        """
        从评估数据中提取peer_review内容
        
        优先提取 overall_comment，如果没有则拼接其他评价内容
        
        Args:
            evaluation: 评估数据字典
            
        Returns:
            提取的评价内容
        """
        # 优先使用 overall_comment
        if evaluation.get('overall_comment'):
            return evaluation['overall_comment'].strip()
        
        # 否则拼接 comments 中的内容
        comments = evaluation.get('comments', {})
        parts = []
        
        if comments.get('strengths'):
            parts.append(f"优点：{comments['strengths']}")
        if comments.get('weaknesses'):
            parts.append(f"不足：{comments['weaknesses']}")
        if comments.get('suggestions'):
            parts.append(f"建议：{comments['suggestions']}")
        
        return '\n'.join(parts).strip() if parts else ""
    
    def get_latest_evaluation_for_work(self, work_id: str, evaluations: List[Dict]) -> Optional[Dict]:
        """
        获取某作品的最新评估（如果有修改历史，获取最后一轮的评估）
        
        Args:
            work_id: 作品ID
            evaluations: 所有评估列表
            
        Returns:
            最新的评估数据，如果没有则返回None
        """
        work_evaluations = [e for e in evaluations if e.get('work_id') == work_id]
        
        if not work_evaluations:
            return None
        
        # 按评估时间排序，获取最新的
        work_evaluations.sort(
            key=lambda x: x.get('evaluation_time', ''),
            reverse=True
        )
        
        return work_evaluations[0]
    
    def extract_dataset_items(self, semester_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        从学期数据中提取数据集条目
        
        Args:
            semester_data: 学期数据字典
            
        Returns:
            数据集条目列表
        """
        items = []
        
        assignments = semester_data['assignments']
        works = semester_data['works']
        evaluations = semester_data['evaluations']
        
        for evaluation in evaluations:
            work_id = evaluation.get('work_id')
            assignment_id = evaluation.get('assignment_id')
            
            # 获取对应的作品和作业
            work = works.get(work_id)
            assignment = assignments.get(assignment_id)
            
            if not work or not assignment:
                continue
            
            # 提取 question（作业题目和要求）
            question = self._format_question(assignment)
            
            # 提取 answer（学生作品内容）
            # 如果有修改历史，使用最后一次修改的内容
            answer = self._get_final_work_content(work)
            
            # 提取 peer_review
            peer_review = self.extract_peer_review(evaluation)
            
            if not peer_review:
                continue
            
            item = {
                "question": question,
                "answer": answer,
                "peer_review": peer_review,
                "ground_truth_label": "",  # 待标注
                # 额外元数据（可选保留）
                "_metadata": {
                    "evaluation_id": evaluation.get('id'),
                    "work_id": work_id,
                    "assignment_id": assignment_id,
                    "evaluator_id": evaluation.get('evaluator_id'),
                    "student_id": work.get('student_id'),
                    "evaluation_time": evaluation.get('evaluation_time'),
                    "scores": evaluation.get('scores', {})
                }
            }
            
            items.append(item)
        
        return items
    
    def _format_question(self, assignment: Dict[str, Any]) -> str:
        """格式化作业题目"""
        parts = []
        
        title = assignment.get('title', '')
        if title:
            parts.append(f"题目：{title}")
        
        description = assignment.get('description', '')
        if description:
            parts.append(f"描述：{description}")
        
        requirements = assignment.get('requirements', [])
        if requirements:
            req_text = '\n'.join(f"  {i+1}. {r}" for i, r in enumerate(requirements))
            parts.append(f"要求：\n{req_text}")
        
        return '\n'.join(parts)
    
    def _get_final_work_content(self, work: Dict[str, Any]) -> str:
        """获取作品的最终内容（如果有修改历史，使用最后一次的内容）"""
        revision_history = work.get('revision_history', [])
        
        if revision_history:
            # 按轮次排序，获取最后一次修改
            revision_history.sort(key=lambda x: x.get('round_number', 0), reverse=True)
            latest_revision = revision_history[0]
            content = latest_revision.get('revised_content', '')
            if content:
                return content
        
        # 使用原始内容
        return work.get('content', '')
    
    def label_with_llm(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        使用大模型批量标注标签
        
        Args:
            items: 待标注的数据条目列表
            
        Returns:
            标注后的数据条目列表
        """
        if not self.use_llm_labeling:
            return items
        
        labeled_items = []
        total = len(items)
        
        for i in range(0, total, self.batch_size):
            batch = items[i:i + self.batch_size]
            print(f"正在标注 {i+1}-{min(i+self.batch_size, total)}/{total} 条数据...")
            
            for item in batch:
                label = self._label_single_item(item)
                item['ground_truth_label'] = label
                labeled_items.append(item)
        
        return labeled_items
    
    def _label_single_item(self, item: Dict[str, Any]) -> str:
        """
        使用大模型标注单个条目
        
        Args:
            item: 数据条目
            
        Returns:
            标签类别
        """
        peer_review = item['peer_review']
        
        # 构建提示词
        prompt = self._build_labeling_prompt(peer_review)
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的文本分类助手，负责对同伴互评内容进行分类标注。请根据评价内容的主要意图，选择最合适的一个类别标签。只输出标签名称，不要有其他内容。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            label = response.choices[0].message.content.strip()
            
            # 验证标签是否有效
            if label in LABEL_CATEGORIES:
                return label
            
            # 尝试模糊匹配
            for category in LABEL_CATEGORIES:
                if category in label:
                    return category
            
            # 默认返回"指导建议"（因为大多数评价都包含建议）
            return "指导建议"
            
        except Exception as e:
            print(f"标注失败: {e}")
            return "其他"
    
    def _build_labeling_prompt(self, peer_review: str) -> str:
        """构建标注提示词"""
        # 如果评价内容过长，截取摘要
        max_length = 2000
        if len(peer_review) > max_length:
            peer_review = peer_review[:max_length] + "..."
        
        label_desc = "\n".join([f"- {cat}: {desc}" for cat, desc in LABEL_DESCRIPTIONS.items()])
        
        prompt = f"""请对以下同伴互评内容进行分类，选择最能代表评价主要意图的标签。

【标签类别说明】
{label_desc}

【评价内容】
{peer_review}

【分类要求】
1. 如果评价内容同时包含多种意图，选择最主要/最突出的一个
2. 如果评价以具体改进建议为主（如"建议..."、"可以尝试..."），选择"指导建议"
3. 如果评价直接指出错误（如"这里错了"、"答案应该是..."），选择"直接修正"
4. 如果评价只是简单的正面肯定（如"很好"、"不错"），选择"支持"
5. 如果评价只是简单的负面批评（如"不太好"），选择"反对"
6. 如果评价包含批判性反思或经验总结，选择"反思评估"
7. 如果评价者表示从作品中学到了新方法/思路，选择"内化迁移"
8. 如果评价只是陈述知识但没有具体建议，选择"不入观点"
9. 如果评价与作品完全无关，选择"无关评语"

请直接输出标签名称（只输出一个词）："""
        
        return prompt
    
    def export_dataset(
        self,
        semester_path: str,
        output_path: str,
        include_metadata: bool = False,
        format_type: str = "json"
    ) -> str:
        """
        导出数据集
        
        Args:
            semester_path: 学期数据目录路径
            output_path: 输出文件路径
            include_metadata: 是否包含元数据
            format_type: 输出格式 ("json" 或 "jsonl")
            
        Returns:
            输出文件的实际路径
        """
        print(f"正在加载学期数据: {semester_path}")
        semester_data = self.load_semester_data(semester_path)
        
        print(f"已加载: {len(semester_data['assignments'])} 个作业, "
              f"{len(semester_data['works'])} 个作品, "
              f"{len(semester_data['evaluations'])} 条评估")
        
        print("正在提取数据集条目...")
        items = self.extract_dataset_items(semester_data)
        print(f"提取到 {len(items)} 条数据")
        
        if self.use_llm_labeling:
            print("正在使用大模型进行标签标注...")
            items = self.label_with_llm(items)
        
        # 处理输出数据
        output_items = []
        for item in items:
            output_item = {
                "question": item["question"],
                "answer": item["answer"],
                "peer_review": item["peer_review"],
                "ground_truth_label": item["ground_truth_label"]
            }
            if include_metadata:
                output_item["_metadata"] = item.get("_metadata", {})
            output_items.append(output_item)
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 保存文件
        if format_type == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in output_items:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_items, f, ensure_ascii=False, indent=2)
        
        print(f"数据集已导出到: {output_path}")
        print(f"共导出 {len(output_items)} 条数据")
        
        # 统计标签分布
        if self.use_llm_labeling:
            self._print_label_statistics(output_items)
        
        return output_path
    
    def _print_label_statistics(self, items: List[Dict[str, Any]]):
        """打印标签分布统计"""
        label_counts = {}
        for item in items:
            label = item.get('ground_truth_label', '其他')
            label_counts[label] = label_counts.get(label, 0) + 1
        
        print("\n【标签分布统计】")
        total = len(items)
        for label in LABEL_CATEGORIES:
            count = label_counts.get(label, 0)
            percentage = (count / total * 100) if total > 0 else 0
            bar = '█' * int(percentage / 2)
            print(f"  {label}: {count:4d} ({percentage:5.1f}%) {bar}")


def find_semester_directories(data_dir: str) -> List[str]:
    """查找所有学期数据目录"""
    semester_dirs = []
    if os.path.exists(data_dir):
        for name in os.listdir(data_dir):
            path = os.path.join(data_dir, name)
            if os.path.isdir(path) and name.startswith('semester_'):
                semester_dirs.append(path)
    return sorted(semester_dirs)


def main():
    parser = argparse.ArgumentParser(
        description="同伴互评数据集导出工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 导出指定学期的数据
  python export_peer_review_dataset.py --semester data/semester_semester_c078e9e6
  
  # 导出所有学期的数据
  python export_peer_review_dataset.py --all
  
  # 不使用大模型标注（只提取数据）
  python export_peer_review_dataset.py --semester data/semester_semester_c078e9e6 --no-labeling
  
  # 导出为JSONL格式
  python export_peer_review_dataset.py --semester data/semester_semester_c078e9e6 --format jsonl
  
  # 包含元数据
  python export_peer_review_dataset.py --semester data/semester_semester_c078e9e6 --include-metadata
        """
    )
    
    parser.add_argument(
        '--semester', '-s',
        type=str,
        help='学期数据目录路径'
    )
    
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='导出所有学期的数据'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='输出文件路径（默认为 output/peer_review_dataset.json）'
    )
    
    parser.add_argument(
        '--no-labeling',
        action='store_true',
        help='不使用大模型进行标签标注'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['json', 'jsonl'],
        default='json',
        help='输出文件格式（默认为json）'
    )
    
    parser.add_argument(
        '--include-metadata', '-m',
        action='store_true',
        help='在输出中包含元数据'
    )
    
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=10,
        help='批量标注时每批的数量（默认为10）'
    )
    
    args = parser.parse_args()
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        output_dir = os.path.join(project_root, 'output')
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ext = 'jsonl' if args.format == 'jsonl' else 'json'
        output_path = os.path.join(output_dir, f'peer_review_dataset_{timestamp}.{ext}')
    
    # 创建导出器
    exporter = PeerReviewDatasetExporter(
        use_llm_labeling=not args.no_labeling,
        batch_size=args.batch_size
    )
    
    if args.all:
        # 导出所有学期
        data_dir = os.path.join(project_root, 'data')
        semester_dirs = find_semester_directories(data_dir)
        
        if not semester_dirs:
            print(f"在 {data_dir} 中未找到学期数据目录")
            return
        
        print(f"找到 {len(semester_dirs)} 个学期数据目录")
        
        all_items = []
        for semester_path in semester_dirs:
            print(f"\n处理: {semester_path}")
            semester_data = exporter.load_semester_data(semester_path)
            items = exporter.extract_dataset_items(semester_data)
            
            if exporter.use_llm_labeling:
                items = exporter.label_with_llm(items)
            
            all_items.extend(items)
        
        # 保存合并后的数据
        output_items = []
        for item in all_items:
            output_item = {
                "question": item["question"],
                "answer": item["answer"],
                "peer_review": item["peer_review"],
                "ground_truth_label": item["ground_truth_label"]
            }
            if args.include_metadata:
                output_item["_metadata"] = item.get("_metadata", {})
            output_items.append(output_item)
        
        if args.format == "jsonl":
            with open(output_path, 'w', encoding='utf-8') as f:
                for item in output_items:
                    f.write(json.dumps(item, ensure_ascii=False) + '\n')
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_items, f, ensure_ascii=False, indent=2)
        
        print(f"\n数据集已导出到: {output_path}")
        print(f"共导出 {len(output_items)} 条数据")
        
        if exporter.use_llm_labeling:
            exporter._print_label_statistics(output_items)
    
    elif args.semester:
        # 导出指定学期
        if not os.path.exists(args.semester):
            print(f"错误: 学期目录不存在: {args.semester}")
            return
        
        exporter.export_dataset(
            semester_path=args.semester,
            output_path=output_path,
            include_metadata=args.include_metadata,
            format_type=args.format
        )
    
    else:
        parser.print_help()
        print("\n请指定 --semester 或 --all 参数")


if __name__ == "__main__":
    main()
