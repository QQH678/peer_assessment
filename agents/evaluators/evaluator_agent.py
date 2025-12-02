import uuid
import random
import re
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import openai
from models.data_models import Student, StudentWork, Assignment, PeerEvaluation, EvaluationScore
from models.psychology_models import StudentPsychology
from config.settings import Config
from config.course_templates import detect_course_type, get_comment_length_limit

class EvaluatorAgent:
    """评估代理，用于模拟学生进行同伴互评"""
    
    def __init__(self, evaluator: Student):
        self.evaluator = evaluator
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        # 初始化或加载心理状态
        self.psychology = self._load_psychology_state()
    
    def _load_psychology_state(self) -> StudentPsychology:
        """加载或创建心理状态"""
        if self.evaluator.psychology_state:
            try:
                return StudentPsychology.from_dict(self.evaluator.psychology_state)
            except:
                pass
        # 根据学生类型创建默认心理状态
        return StudentPsychology.create_default(self.evaluator.student_type.value)
    
    def _save_psychology_state(self):
        """保存心理状态到学生模型"""
        self.evaluator.psychology_state = self.psychology.to_dict()
    
    def initialize_social_relationships(self, all_student_ids: List[str]):
        """
        初始化与其他学生的社交关系
        
        在真实场景中，学生在开学前可能就有一些社交关系：
        - 同乡、室友、社团成员可能是朋友
        - 某些人天生性格不合
        - 大部分人是陌生人（中性关系）
        
        Args:
            all_student_ids: 班级中所有学生的ID列表
        """
        for other_id in all_student_ids:
            if other_id == self.evaluator.id:
                continue  # 跳过自己
            
            # 如果已经有关系记录，不覆盖
            if other_id in self.psychology.social.relationships:
                continue
            
            # 根据概率随机生成初始关系
            rand = random.random()
            
            if rand < 0.08:  # 8%概率是好朋友
                relationship = random.uniform(0.4, 0.8)
            elif rand < 0.13:  # 5%概率是不太对付的人
                relationship = random.uniform(-0.6, -0.2)
            elif rand < 0.25:  # 12%概率是普通认识
                relationship = random.uniform(0.1, 0.3)
            else:  # 75%概率是陌生人
                relationship = 0.0
            
            if relationship != 0.0:
                self.psychology.social.relationships[other_id] = relationship
        
        # 保存更新后的心理状态
        self._save_psychology_state()
    
    def evaluate_work(self, work: StudentWork, assignment: Assignment, 
                     work_author: Student) -> PeerEvaluation:
        """评估学生作品"""
        
        # 获取社交关系影响的分数偏差
        reciprocity_bias = self.psychology.social.get_evaluation_bias(work_author.id)
        
        # 构建评估提示词（包含心理状态影响）
        prompt = self._build_evaluation_prompt(work, assignment, work_author)
        
        # 调用LLM进行评估
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": self._build_system_prompt(assignment)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            
            # 应用个性化语言风格后处理（已禁用）
            # content = self._apply_language_style(content)
            
            # 调试：打印LLM响应内容
            print(f" === LLM响应内容 ===")
            print(f"评估者: {self.evaluator.name} ({self.evaluator.student_type.value})")
            print(f"心情: 动力{self.psychology.emotion.motivation:.1f}, 信心{self.psychology.emotion.confidence:.1f}")
            print(f"与{work_author.name}的关系偏差: {reciprocity_bias:+.1f}")
            print(f"响应长度: {len(content)} 字符")
            print(f"响应内容:")
            print(content)
            print("=" * 50)
            
            # 解析评估结果
            evaluation = self._create_peer_evaluation(work, assignment, content, reciprocity_bias)
            
            # 更新社交关系
            self._update_social_relationship(work_author.id, evaluation)
            
            # 保存心理状态
            self._save_psychology_state()
            
            return evaluation
            
        except Exception as e:
            print(f"生成评价时出错: {e}")
            return self._generate_default_evaluation_object(work, assignment)
    
    def _build_system_prompt(self, assignment: Assignment = None) -> str:
        """构建系统提示词"""
        
        # 根据学生类型获取评估风格
        style_description = self._get_evaluation_style_description()
        
        # 获取心情相关的提示
        mood_addon = self._get_mood_based_prompt_addon()
        
        # 获取语言风格提示
        language_style_prompt = self.psychology.language.get_style_prompt()
        
        # 获取字数限制（如果有assignment）
        length_requirement = ""
        if assignment:
            course_type = detect_course_type(assignment.subject)
            length_limit = get_comment_length_limit(course_type)
            length_requirement = f"""

❗ 重要：字数要求
- 评价字数范围：{length_limit['min']}-{length_limit['max']}字（中文）
- 说明：{length_limit['description']}
- 请保持简洁，避免冗长，说明要点即可
- 不要为了凑字数而重复内容，也不要写得过于简略"""
        else:
            length_requirement = """

❗ 重要：字数要求
- 评价字数范围：60-120字（中文）
- 请保持简洁，避免冗长"""
        
        return f"""你是一名{self.evaluator.major}专业的{self.evaluator.academic_level}学生，名字叫{self.evaluator.name}。
{length_requirement}

评估者特征：
- 学生类型：{self.evaluator.student_type.value}
- GPA：{self.evaluator.gpa}
- 编程经验：{self.evaluator.programming_experience}年
- 性格特征：{self.evaluator.personality_traits}

{style_description}

🎭 当前状态：
- 动力值：{self.psychology.emotion.motivation:.0%}
- 自信度：{self.psychology.emotion.confidence:.0%}
- 疲劳度：{self.psychology.emotion.fatigue:.0%}
{mood_addon}

📝 你的表达风格：
{language_style_prompt}

⚠️⚠️⚠️ 关键评分说明 ⚠️⚠️⚠️
每个维度都是独立评分，每个维度的满分都是100分！
不要把总分拆分到各维度，而是每个维度单独评价！

举例说明（正确）：
- 功能实现: 75分（这个维度满分100）
- 代码质量: 70分（这个维度满分100）
- 创新性: 65分（这个维度满分100）
- 文档完整性: 72分（这个维度满分100）

⚠️ 错误示范（不要这样做）：
- 功能实现: 28分 ❌ （太低了！）
- 代码质量: 21分 ❌ （太低了！）

评分指导：
- 这是同伴互评，以鼓励和帮助为主
- 完成了基本要求的作业，每个维度至少70分
- 有明显优点的可以给80-90分
- 只有几乎没有内容的才给60分以下

各维度评分参考（每个维度满分100）：
- 90-100分：该维度表现优秀
- 80-89分：该维度表现良好
- 70-79分：该维度完成了基本要求
- 60-69分：该维度需要改进
- 60以下：该维度严重不足

请按以下格式输出（注意：每个分数都应该在60-100之间）：

=== 评分 ===
功能实现: [70-100分]
代码质量: [70-100分] 
创新性: [60-100分]
文档完整性: [60-100分]

=== 我的评价 ===
[用自然的语言写出你对这个作业的真实看法。
⚠️ 严格遵守前面提到的字数要求！
简明扼要地说明：作业完成情况、主要优点、需要改进的地方、具体建议]

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
                              content: str, reciprocity_bias: float = 0.0) -> PeerEvaluation:
        """从LLM响应创建同伴评估对象"""
        
        # 解析评估内容
        sections = self._parse_evaluation_response(content)
        
        # 提取分数
        scores = self._extract_scores_from_new_format(sections)
        
        # 应用学生类型偏差和社交关系偏差
        adjusted_scores = self._apply_student_bias(scores, reciprocity_bias)
        
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
    
    def _apply_student_bias(self, scores: Dict[str, int], reciprocity_bias: float = 0.0) -> Dict[str, int]:
        """根据学生类型应用评分偏差，并校验分数合理性
        
        注意：情绪偏差和社交关系偏差已禁用
        """
        student_type = self.evaluator.student_type.value
        type_config = Config.STUDENT_TYPES.get(student_type, {})
        bias = type_config.get("score_bias", 0.0)
        
        # 情绪偏差已禁用
        # mood = self.psychology.emotion
        # mood_bias = 0.0
        # if mood.motivation > 0.55:
        #     mood_bias += (mood.motivation - 0.5) * 10
        # elif mood.motivation < 0.45:
        #     mood_bias -= (0.5 - mood.motivation) * 10
        # if mood.frustration > 0.4:
        #     mood_bias -= mood.frustration * 6
        # if mood.fatigue > 0.5:
        #     mood_bias += random.uniform(-4, 4) * mood.fatigue
        
        adjusted_scores = {}
        for dimension, score in scores.items():
            # 检测LLM是否错误地按百分制总分拆分（分数低于50通常是错误的）
            if score < 50:
                # 可能是LLM按总分100拆分到4个维度了，需要校正
                print(f"⚠️ 检测到异常低分 {dimension}: {score}分，进行校正...")
                score = max(65, score + 45)
            
            # 只应用学生类型偏差（社交关系偏差和情绪偏差已禁用）
            total_bias = (bias * 100)  # + reciprocity_bias + mood_bias
            adjusted_score = score + total_bias
            
            # 添加随机性
            random_factor = random.uniform(-5, 5)
            adjusted_score += random_factor
            
            # 确保分数在有效范围内（最低60分，最高100分）
            adjusted_score = max(60, min(100, int(adjusted_score)))
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
        
        # 根据评估者特征生成基础分数（提高基线，鼓励性评价）
        base_score = 75 + (self.evaluator.gpa - 3.0) * 8
        
        # 应用严格程度调整
        type_config = Config.STUDENT_TYPES.get(self.evaluator.student_type.value, {})
        strictness_adjustment = (1 - type_config.get("strictness", 0.6)) * 12
        final_score = base_score + strictness_adjustment + random.uniform(-8, 8)
        final_score = max(50, min(100, final_score))
        
        # 生成各维度分数（提高下限）
        scores = {}
        for dim in ["functionality", "code_quality", "innovation", "documentation"]:
            dim_score = final_score + random.uniform(-6, 6)
            scores[dim] = max(45, min(100, int(dim_score)))
        
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
        """根据学生类型获取默认分数（基准提高，鼓励性评价）"""
        student_type = self.evaluator.student_type.value
        
        if student_type == "excellent":
            return random.randint(78, 92)
        elif student_type == "good":
            return random.randint(75, 88)
        elif student_type == "average":
            return random.randint(72, 85)
        elif student_type == "below_average":
            return random.randint(68, 82)
        elif student_type == "strict":
            return random.randint(65, 78)
        elif student_type == "lenient":
            return random.randint(82, 95)
        elif student_type == "perfunctory":
            return random.randint(75, 88)  # 敷衍学生随意给分，偏中上
        else:
            return 75
    
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

    def _apply_language_style(self, content: str) -> str:
        """应用个性化语言风格到评价内容"""
        style = self.psychology.language
        emotion = self.psychology.emotion
        
        # 总是应用语言风格处理（包含打字错误、表情等）
        # 原条件太苛刻，改为始终应用
        content = style.apply_style_to_comment(content, emotion.current_mood)
        
        # 降低emoji添加阈值：动力>0.4 且 emoji倾向>0.1 即可
        if emotion.motivation > 0.4 and style.emoji_tendency > 0.1:
            content = self._add_mood_based_emoji(content)
        
        # 根据正式程度调整用语
        if style.formality < 0.4:
            content = self._make_informal(content)
        
        # 添加口头禅或常用语
        if style.catchphrases and random.random() < 0.3:
            phrase = random.choice(style.catchphrases)
            # 在评价末尾或开头添加
            if random.random() < 0.5:
                content = phrase + " " + content
            else:
                content = content.rstrip("。！？") + "～ " + phrase
        
        return content
    
    def _add_mood_based_emoji(self, content: str) -> str:
        """根据情绪添加表情符号"""
        emotion = self.psychology.emotion
        
        positive_emojis = ["👍", "😊", "🎉", "✨", "💪", "🌟", "👏"]
        neutral_emojis = ["🤔", "📝", "💡", "🔍"]
        negative_emojis = ["😅", "🥲", "😓"]
        
        # 选择表情
        if emotion.motivation > 0.7:
            emoji = random.choice(positive_emojis)
        elif emotion.frustration > 0.5:
            emoji = random.choice(negative_emojis)
        else:
            emoji = random.choice(neutral_emojis)
        
        # 在句子末尾添加
        sentences = content.split("。")
        if len(sentences) > 1 and random.random() < self.psychology.language.emoji_tendency:
            idx = random.randint(0, min(2, len(sentences) - 2))
            sentences[idx] = sentences[idx] + emoji
            content = "。".join(sentences)
        
        return content
    
    def _make_informal(self, content: str) -> str:
        """将内容变得不那么正式"""
        replacements = {
            "非常": random.choice(["很", "超", "特别"]),
            "建议": random.choice(["觉得可以", "感觉能"]),
            "需要": random.choice(["得", "要"]),
            "应该": random.choice(["可以", "最好"]),
            "希望": random.choice(["期待", "想看到"]),
            "优秀": random.choice(["厉害", "棒", "牛"]),
            "良好": random.choice(["不错", "挺好的"]),
            "不足": random.choice(["差点", "还差点意思"]),
        }
        
        for formal, informal in replacements.items():
            if formal in content and random.random() < 0.5:
                content = content.replace(formal, informal, 1)
        
        return content
    
    def _update_social_relationship(self, author_id: str, evaluation: PeerEvaluation):
        """更新与被评价者的社交关系"""
        # 计算平均分
        avg_score = evaluation.scores.total_score() / 4
        
        # 根据评分更新关系（高分增进关系，低分减少好感）
        if avg_score >= 80:
            relationship_change = 0.1
        elif avg_score >= 70:
            relationship_change = 0.05
        elif avg_score >= 60:
            relationship_change = 0
        else:
            relationship_change = -0.1
        
        # 更新关系分数
        current_score = self.psychology.social.relationships.get(author_id, 0.0)
        new_score = max(-1, min(1, current_score + relationship_change))
        self.psychology.social.relationships[author_id] = new_score
        
        # 记录互惠记忆（分数偏差）
        expected_score = 70  # 假设期望分数
        score_deviation = (avg_score - expected_score) / 100.0
        self.psychology.social.reciprocity_memory[author_id] = score_deviation
    
    def _get_mood_based_prompt_addon(self) -> str:
        """根据当前心情生成额外的提示"""
        emotion = self.psychology.emotion
        
        addons = []
        
        # 降低阈值使心情效果更容易触发
        if emotion.fatigue > 0.5:
            addons.append("你现在有点累了，可能会评价得简短一些。")
        
        if emotion.frustration > 0.4:
            addons.append("你今天心情不太好，可能会更挑剔一些。")
        elif emotion.motivation > 0.6:
            addons.append("你今天状态很好，会更积极地发现优点。")
        
        if emotion.confidence < 0.5:
            addons.append("你对自己的判断不太自信，会使用更保守的措辞。")
        
        return " ".join(addons) if addons else ""
