import uuid
import random
import re
from datetime import datetime
from typing import Dict, Any, List
import openai
from models.data_models import Student, StudentWork, Assignment, PeerEvaluation, EvaluationScore
from config.settings import Config

class EvaluatorAgent:
    """评估代理，用于模拟学生进行同伴互评"""
    
    def __init__(self, evaluator: Student):
        self.evaluator = evaluator
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
    
    def evaluate_work(self, work: StudentWork, assignment: Assignment, 
                     work_author: Student) -> PeerEvaluation:
        """评估学生作品"""
        
        # 构建评估提示词
        prompt = self._build_evaluation_prompt(work, assignment, work_author)
        
        # 调用LLM进行评估
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": self._get_evaluator_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # 调试：打印LLM响应内容
            print(f" === LLM响应内容 ===")
            print(f"评估者: {self.evaluator.name} ({self.evaluator.student_type.value})")
            print(f"响应长度: {len(content)} 字符")
            print(f"响应内容:")
            print(content)
            print("=" * 50)
            
            # 解析评估结果
            return self._create_peer_evaluation(work, assignment, content)
            
        except Exception as e:
            print(f"生成评价时出错: {e}")
            return self._generate_default_evaluation_object(work, assignment)
    
    def _get_evaluator_system_prompt(self) -> str:
        """获取评估者的系统提示词"""
        
        # 根据学生类型调整评估风格
        style_description = self._get_evaluation_style_description()
        
        return f"""你是一名{self.evaluator.major}专业的{self.evaluator.academic_level}学生，名字叫{self.evaluator.name}。

评估者特征：
- 学生类型：{self.evaluator.student_type.value}
- GPA：{self.evaluator.gpa}
- 编程经验：{self.evaluator.programming_experience}年
- 性格特征：{self.evaluator.personality_traits}

{style_description}

请像真实的学生一样，用自然的语言对同学的作业进行评价。不要使用生硬的条条框框，而是写出真实的想法和建议,但字数也不需要太多。

请按以下格式输出：

=== 评分 ===
功能实现: [0-100分]
代码质量: [0-100分] 
创新性: [0-100分]
文档完整性: [0-100分]

=== 我的评价 ===
[用自然的语言写出你对这个作业的真实看法，就像和同学聊天一样。包括：
- 你觉得这个作业做得怎么样
- 有什么地方做得特别好
- 有什么需要改进的地方
- 给同学的建议
- 你的整体感受]

=== 评估用时 ===
[评估这个作业大概花费的分钟数]
"""
    
    def _get_evaluation_style_description(self) -> str:
        """根据学生类型获取评估风格描述"""
        
        student_type = self.evaluator.student_type.value
        
        if student_type == "excellent":
            return """你是个学霸，看问题很准确，会指出作业的优点和不足，评价比较中肯客观。
你会用专业的术语，但也会用同学能理解的方式表达。你习惯给出具体的改进建议。"""
        elif student_type == "good":
            return """你学习不错，评价比较客观，会鼓励同学，也会指出问题。
你的表达比较友善，会站在同学的角度考虑问题。有时候可能对一些高级技术理解不够深入。"""
        elif student_type == "average":
            return """你是个普通学生，评价相对客观，但可能看不出一些深层次的问题。
你会用比较简单直白的语言，重点关注作业是否完成了基本要求。"""
        elif student_type == "below_average":
            return """你的基础相对薄弱，评价可能不够准确，容易忽略一些重要问题。
你会更多关注表面现象，可能对技术细节理解有限，但会尽力给出自己的看法。"""
        elif student_type == "strict":
            return """你要求很严格，标准很高，经常能找出各种问题和不足。
你的评价比较犀利，给分偏低，会详细指出需要改进的地方，有时候可能有点苛刻。"""
        elif student_type == "lenient":
            return """你比较宽松友善，喜欢鼓励同学，往往能发现作业的优点。
你不太愿意给出严厉的批评，更愿意给出正面的反馈和温和的建议。"""
        elif student_type == "perfunctory":
            return """你比较敷衍，你发现不了同学的什么问题，你总是会回复不相关的内容，有时候只会回个哈哈哈，
            嗯嗯嗯之类的内容"""
        else:
            return "请根据你的水平和性格特点进行评价。"
    
    def _build_evaluation_prompt(self, work: StudentWork, assignment: Assignment,
                               work_author: Student) -> str:
        """构建评估提示词"""
        
        prompt = f"""现在需要你评价一个同学的作业：

【作业信息】
标题：{assignment.title}
类型：{assignment.assignment_type.value}
课程：{assignment.subject}
难度：{assignment.difficulty_level}/5
描述：{assignment.description}

【同学的作品】
{work.content}

【作品说明】
{work.documentation or "（这位同学没有提供额外说明）"}

【作者背景】
专业：{work_author.major}
学术水平：{work_author.academic_level}

【作者的自我评价】"""
        
        if work.self_assessment:
            for dimension, score in work.self_assessment.items():
                prompt += f"\n{dimension}: {score}分"
        else:
            prompt += "\n（这位同学没有做自我评价）"
        
        prompt += f"""

现在请你像真实的同学一样，认真看看这个作业，然后给出你的评价。

记住，你需要给出具体的分数，但更重要的是要写出你真实的想法和建议！"""
        
        return prompt
    
    def _create_peer_evaluation(self, work: StudentWork, assignment: Assignment,
                              content: str) -> PeerEvaluation:
        """从LLM响应创建同伴评估对象"""
        
        # 解析评估内容
        sections = self._parse_evaluation_response(content)
        
        # 提取分数
        scores = self._extract_scores_from_new_format(sections)
        
        # 应用学生类型偏差
        adjusted_scores = self._apply_student_bias(scores)
        
        # 创建评估分数对象
        evaluation_scores = EvaluationScore(
            functionality=adjusted_scores.get("功能实现", 70),
            code_quality=adjusted_scores.get("代码质量", 70),
            innovation=adjusted_scores.get("创新性", 70),
            documentation=adjusted_scores.get("文档完整性", 70)
        )
        
        # 提取自然语言评价，使用更灵活的方法
        natural_comment = ""
        
        # 尝试多种方式提取评价内容
        possible_keys = ["我的评价", "总体评价", "评价", "评语", "意见"]
        for key in possible_keys:
            if key in sections and sections[key].strip():
                natural_comment = sections[key].strip()
                break
        
        # 如果还是没找到，尝试从整个响应中提取有用内容
        if not natural_comment:
            # 移除分数相关的行，保留评价文本
            content_lines = content.split('\n')
            evaluation_lines = []
            for line in content_lines:
                # 跳过包含分数格式的行
                if not re.search(r'[：:]\s*\d+', line) and not line.startswith('===') and line.strip():
                    evaluation_lines.append(line.strip())
            
            if evaluation_lines:
                natural_comment = '\n'.join(evaluation_lines)
        
        # 最后的备用方案
        if not natural_comment:
            natural_comment = "这个作业整体完成得还可以。"
        
        print(f"提取的评价内容: {natural_comment[:100]}...")  # 调试信息
        
        # 解析评估用时
        time_spent = self._parse_evaluation_time(sections.get("评估用时", ""))
        
        return PeerEvaluation(
            id=str(uuid.uuid4()),
            evaluator_id=self.evaluator.id,
            work_id=work.id,
            assignment_id=assignment.id,
            scores=evaluation_scores,
            comments={"overall": natural_comment},  # 只保存整体评价
            overall_comment=natural_comment,
            evaluation_time=datetime.now(),
            time_spent_minutes=time_spent
        )
    
    def _parse_evaluation_response(self, content: str) -> Dict[str, str]:
        """解析评估响应"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('=== ') and line.endswith(' ==='):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[4:-4]
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        return sections
    
    def _extract_scores_from_new_format(self, sections: Dict[str, str]) -> Dict[str, int]:
        """从新格式的评分部分提取分数"""
        import re
        
        scores = {}
        
        if "评分" in sections:
            score_text = sections["评分"]
            dimensions = ["功能实现", "代码质量", "创新性", "文档完整性"]
            
            for dim in dimensions:
                # 寻找 "维度: XX分" 的模式
                patterns = [
                    f"{dim}[：:]\\s*(\\d+)",
                    f"{dim}.*?(\\d+)分",
                    f"{dim}.*?(\\d+)$"
                ]
                
                found_score = None
                for pattern in patterns:
                    match = re.search(pattern, score_text)
                    if match:
                        found_score = int(match.group(1))
                        break
                
                if found_score is not None:
                    scores[dim] = found_score
                else:
                    # 如果没找到，使用默认分数
                    scores[dim] = self._get_default_score()
        else:
            # 如果没有评分部分，使用默认分数
            dimensions = ["功能实现", "代码质量", "创新性", "文档完整性"]
            for dim in dimensions:
                scores[dim] = self._get_default_score()
        
        return scores
        """从各个维度的评价中提取分数"""
        import re
        
        scores = {}
        dimensions = ["功能实现评分", "代码质量评分", "创新性评分", "文档完整性评分"]
        dimension_keys = ["功能实现", "代码质量", "创新性", "文档完整性"]
        
        for i, dim in enumerate(dimensions):
            if dim in sections:
                # 寻找分数模式
                score_match = re.search(r'分数[：:]\s*(\d+)', sections[dim])
                if score_match:
                    scores[dimension_keys[i]] = int(score_match.group(1))
                else:
                    # 如果没找到，使用默认分数
                    scores[dimension_keys[i]] = self._get_default_score()
            else:
                scores[dimension_keys[i]] = self._get_default_score()
        
        return scores
    
    def _apply_student_bias(self, scores: Dict[str, int]) -> Dict[str, int]:
        """根据学生类型应用评分偏差"""
        student_type = self.evaluator.student_type.value
        type_config = Config.STUDENT_TYPES.get(student_type, {})
        bias = type_config.get("score_bias", 0.0)
        
        adjusted_scores = {}
        for dimension, score in scores.items():
            # 应用偏差
            adjusted_score = score + (bias * 100)
            
            # 添加随机性
            random_factor = random.uniform(-5, 5)
            adjusted_score += random_factor
            
            # 确保分数在有效范围内
            adjusted_score = max(0, min(100, int(adjusted_score)))
            adjusted_scores[dimension] = adjusted_score
        
        return adjusted_scores
    
    def _extract_comments(self, sections: Dict[str, str]) -> Dict[str, str]:
        """提取各维度的评价意见"""
        import re
        
        comments = {}
        dimensions = ["功能实现评分", "代码质量评分", "创新性评分", "文档完整性评分"]
        dimension_keys = ["功能实现", "代码质量", "创新性", "文档完整性"]
        
        for i, dim in enumerate(dimensions):
            if dim in sections:
                # 提取评价部分（分数后的内容）
                content = sections[dim]
                # 移除分数行，保留评价内容
                lines = content.split('\n')
                comment_lines = []
                for line in lines:
                    if not re.search(r'分数[：:]\s*\d+', line):
                        comment_lines.append(line)
                
                comment = '\n'.join(comment_lines).strip()
                if comment and not comment.startswith('评价'):
                    comments[dimension_keys[i]] = comment
                else:
                    # 如果找不到评价，提取评价:后的内容
                    eval_match = re.search(r'评价[：:]\s*(.+)', content, re.DOTALL)
                    if eval_match:
                        comments[dimension_keys[i]] = eval_match.group(1).strip()
                    else:
                        comments[dimension_keys[i]] = "评价内容"
            else:
                comments[dimension_keys[i]] = "无具体评价"
        
        return comments
    
    def _generate_default_evaluation_object(self, work: StudentWork, assignment: Assignment) -> PeerEvaluation:
        """生成默认评估对象（当API调用失败时）"""
        
        # 根据评估者特征生成基础分数
        base_score = 70 + (self.evaluator.gpa - 3.0) * 10
        
        # 应用严格程度调整
        type_config = Config.STUDENT_TYPES.get(self.evaluator.student_type.value, {})
        strictness_adjustment = (1 - type_config.get("strictness", 0.6)) * 15
        final_score = base_score + strictness_adjustment + random.uniform(-10, 10)
        final_score = max(30, min(100, final_score))
        
        # 生成各维度分数
        scores = {}
        for dim in ["functionality", "code_quality", "innovation", "documentation"]:
            dim_score = final_score + random.uniform(-8, 8)
            scores[dim] = max(20, min(100, int(dim_score)))
        
        evaluation_scores = EvaluationScore(**scores)
        
        # 生成简单的评价
        student_type = self.evaluator.student_type.value
        if student_type == "strict":
            comment = "这个作业还有不少需要改进的地方，希望能更加仔细。"
        elif student_type == "lenient":
            comment = "做得不错！继续加油，我看到了你的努力。"
        else:
            comment = f"这个作业完成得还可以，有{random.choice(['亮点', '特色', '值得学习的地方'])}。"
        
        return PeerEvaluation(
            id=str(uuid.uuid4()),
            evaluator_id=self.evaluator.id,
            work_id=work.id,
            assignment_id=assignment.id,
            scores=evaluation_scores,
            comments={"overall": comment},
            overall_comment=comment,
            evaluation_time=datetime.now(),
            time_spent_minutes=random.randint(10, 25)
        )
    
    def _get_default_score(self) -> int:
        """根据学生类型获取默认分数"""
        student_type = self.evaluator.student_type.value
        
        if student_type == "excellent":
            return random.randint(75, 90)
        elif student_type == "good":
            return random.randint(70, 85)
        elif student_type == "average":
            return random.randint(65, 80)
        elif student_type == "below_average":
            return random.randint(60, 75)
        elif student_type == "strict":
            return random.randint(55, 70)
        elif student_type == "lenient":
            return random.randint(80, 95)
        elif student_type == "perfunctory":
            return random.randint(70, 85)  # 敷衍学生随意给分，偏中上
        else:
            return 70
    
    def _parse_evaluation_time(self, time_text: str) -> int:
        """解析评估用时"""
        import re
        
        try:
            numbers = re.findall(r'\d+', time_text)
            if numbers:
                return int(numbers[0])
        except:
            pass
        
        # 根据学生类型返回默认用时
        if self.evaluator.student_type.value == "excellent":
            return random.randint(15, 25)
        elif self.evaluator.student_type.value == "strict":
            return random.randint(20, 30)
        else:
            return random.randint(10, 20)
