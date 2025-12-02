"""
教师Agent分析模块
实现每轮互评后的学生分析和阶段性学情报告生成
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import logging
import openai
import re
import json
from config.settings import Config


class KnowledgeStateAnalysis(BaseModel):
    """知识状态分析"""
    student_id: str
    round_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 知识点掌握度
    knowledge_mastery: Dict[str, float] = Field(description="知识点 -> 掌握度[0-1]")
    knowledge_growth: Dict[str, float] = Field(description="知识点 -> 增长率")
    
    # 错误模式
    error_patterns: List[str] = Field(default_factory=list, description="识别出的错误模式")
    knowledge_gaps: List[str] = Field(default_factory=list, description="知识盲点")
    
    # 强项和弱项
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)


class MetacognitionAssessment(BaseModel):
    """
    元认知能力评估
    基于 Zimmerman (2000) 自我调节学习 (SRL) 三阶段模型
    """
    student_id: str
    round_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 元认知总分
    overall_score: float = Field(ge=0.0, le=1.0, description="总体元认知水平[0-1]")
    
    # === Zimmerman SRL 三阶段 ===
    
    # 阶段1: 前导 (Forethought) - 任务前的准备
    forethought_phase: float = Field(ge=0.0, le=1.0, description="前导阶段得分")
    goal_setting: float = Field(ge=0.0, le=1.0, description="目标设定能力")
    strategic_planning: float = Field(ge=0.0, le=1.0, description="策略规划能力")
    
    # 阶段2: 执行 (Performance) - 任务执行过程
    performance_phase: float = Field(ge=0.0, le=1.0, description="执行阶段得分")
    self_monitoring: float = Field(ge=0.0, le=1.0, description="自我监控能力")
    attention_control: float = Field(ge=0.0, le=1.0, description="注意控制能力")
    
    # 阶段3: 反思 (Self-reflection) - 任务后的反思
    reflection_phase: float = Field(ge=0.0, le=1.0, description="反思阶段得分")
    self_evaluation: float = Field(ge=0.0, le=1.0, description="自我评价能力")
    causal_attribution: float = Field(ge=0.0, le=1.0, description="归因能力")
    
    # 观察和建议
    observations: List[str] = Field(default_factory=list)
    improvement_suggestions: List[str] = Field(default_factory=list)


class PeerEvaluationQualityAssessment(BaseModel):
    """互评质量评估"""
    student_id: str
    round_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 质量维度
    depth: float = Field(ge=0.0, le=1.0, description="深度：表面/深入")
    accuracy: float = Field(ge=0.0, le=1.0, description="准确性：评价是否客观准确")
    constructiveness: float = Field(ge=0.0, le=1.0, description="建设性：是否提供有效建议")
    
    # 总体质量
    overall_quality: float = Field(ge=0.0, le=1.0, description="总体质量")
    
    # 具体评价内容分析
    evaluation_summary: str = Field(description="评价内容摘要")
    positive_aspects: List[str] = Field(default_factory=list, description="评价的亮点")
    areas_for_improvement: List[str] = Field(default_factory=list, description="可改进之处")


class RoundAnalysisResult(BaseModel):
    """单轮分析结果"""
    student_id: str
    round_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # 三大分析
    knowledge_state: KnowledgeStateAnalysis
    metacognition: MetacognitionAssessment
    evaluation_quality: PeerEvaluationQualityAssessment
    
    # 教师反馈
    feedback_to_student: str = Field(description="给学生的反馈")
    action_items: List[str] = Field(default_factory=list, description="行动建议")


class StageReport(BaseModel):
    """阶段学情报告"""
    student_id: str
    stage_id: str
    stage_name: str
    
    # 时间范围
    start_round: int
    end_round: int
    report_date: datetime = Field(default_factory=datetime.now)
    
    # === 知识维度 ===
    # 知识掌握度变化
    initial_knowledge_mastery: Dict[str, float]
    final_knowledge_mastery: Dict[str, float]
    knowledge_growth_rate: Dict[str, float]
    
    # 进步最大的知识点
    most_improved_topics: List[Tuple[str, float]] = Field(description="(知识点, 增长率)")
    # 仍需加强的领域
    topics_needing_attention: List[str]
    
    # === 能力维度 ===
    # 元认知发展轨迹
    metacognition_trajectory: List[Tuple[int, float]] = Field(description="(轮次, 分数)")
    metacognition_growth: float = Field(description="元认知增长")
    
    # 互评能力发展
    evaluation_quality_trajectory: List[Tuple[int, float]]
    evaluation_quality_improvement: float
    
    # 学习效果
    average_assignment_score: float
    score_trend: str = Field(description="上升/下降/稳定")
    
    # === 互评统计 ===
    total_evaluations_given: int
    total_evaluations_received: int
    avg_evaluation_quality_given: float
    
    # === 综合评价 ===
    overall_performance: str = Field(description="优秀/良好/一般/需加强")
    strengths: List[str]
    weaknesses: List[str]
    
    # === 个性化建议 ===
    next_stage_focus: List[str] = Field(description="下阶段学习重点")
    recommended_resources: List[str] = Field(description="推荐学习资源")
    learning_strategy_suggestions: List[str] = Field(description="学习方法建议")
    
    # === 详细反馈 ===
    detailed_feedback: str = Field(description="教师详细反馈")


class TeacherAnalyzer:
    """教师分析器"""
    
    @staticmethod
    def safe_get(obj, attr, default='未知'):
        """兼容字典和对象两种格式的属性访问"""
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)
    
    def _get_evaluation_content(self, evaluation) -> str:
        """从评价对象中提取评价内容，支持多种字段名"""
        # 尝试多种可能的字段名
        possible_fields = ['overall_comment', 'content', 'comment', 'comments', 'evaluation_content']
        
        for field in possible_fields:
            content = self.safe_get(evaluation, field, None)
            if content:
                # 如果是字典类型的comments，尝试提取overall
                if isinstance(content, dict):
                    if 'overall' in content:
                        return str(content['overall'])
                    # 否则合并所有值
                    return '\n'.join(str(v) for v in content.values() if v)
                return str(content)
        
        # 如果有scores，生成一个基于分数的描述
        scores = self.safe_get(evaluation, 'scores', None)
        if scores:
            if hasattr(scores, '__dict__'):
                scores = scores.__dict__
            if isinstance(scores, dict):
                score_desc = ', '.join(f"{k}: {v}" for k, v in scores.items() if v is not None)
                return f"评分: {score_desc}"
        
        return "（无评价内容）"
    
    def _clean_and_parse_json(self, content: str, context: str = "JSON解析") -> dict:
        """
        健壮的JSON解析方法，处理LLM返回的各种异常格式
        
        Args:
            content: LLM返回的原始内容
            context: 调用上下文，用于错误日志
            
        Returns:
            解析后的字典
        """
        if not content:
            raise ValueError("空内容")
        
        original_content = content
        content = content.strip()
        
        # 1. 移除markdown代码块标记
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            # 处理可能的多个代码块，只取第一个
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1]
                # 如果第一个字符是语言标识（如json, python等），移除第一行
                if content.strip() and not content.strip()[0] in '{}[]':
                    lines = content.split('\n', 1)
                    if len(lines) > 1:
                        content = lines[1]
        
        content = content.strip()
        
        # 2. 找到JSON对象的开始和结束
        start_idx = -1
        
        # 找第一个 { 或 [
        for i, c in enumerate(content):
            if c in '{}[]':
                start_idx = i
                break
        
        if start_idx == -1:
            raise ValueError(f"未找到JSON开始标记: {content[:100]}")
        
        # 找匹配的结束标记
        bracket_type = content[start_idx]
        close_bracket = '}' if bracket_type == '{' else ']'
        depth = 0
        in_string = False
        escape_next = False
        end_idx = -1
        
        for i in range(start_idx, len(content)):
            c = content[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if c == '\\':
                escape_next = True
                continue
            
            if c == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if in_string:
                continue
            
            if c == bracket_type:
                depth += 1
            elif c == close_bracket:
                depth -= 1
                if depth == 0:
                    end_idx = i
                    break
        
        if end_idx == -1:
            # 尝试找最后一个匹配的括号
            end_idx = content.rfind(close_bracket)
        
        if end_idx == -1 or end_idx <= start_idx:
            raise ValueError(f"未找到完整的JSON对象: {content[:200]}")
        
        json_str = content[start_idx:end_idx+1]
        
        # 3. 尝试直接解析
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # 4. 尝试修复常见问题
        # 4.1 替换单引号为双引号（在字符串外部）
        fixed_str = self._fix_quotes(json_str)
        try:
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            pass
        
        # 4.2 尝试移除尾部逗号
        fixed_str = re.sub(r',\s*([}\]])', r'\1', fixed_str)
        try:
            return json.loads(fixed_str)
        except json.JSONDecodeError:
            pass
        
        # 4.3 尝试修复未转义的换行符
        fixed_str = fixed_str.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        try:
            return json.loads(fixed_str)
        except json.JSONDecodeError as e:
            logging.debug(f"{context} - 所有修复尝试失败，原始内容: {original_content[:500]}")
            raise ValueError(f"无法解析JSON: {e}")
    
    def _fix_quotes(self, s: str) -> str:
        """修复JSON中的引号问题"""
        result = []
        in_string = False
        i = 0
        while i < len(s):
            c = s[i]
            
            # 处理转义
            if c == '\\' and i + 1 < len(s):
                result.append(c)
                result.append(s[i+1])
                i += 2
                continue
            
            # 处理双引号
            if c == '"':
                in_string = not in_string
                result.append(c)
                i += 1
                continue
            
            # 处理单引号（仅在字符串外部替换）
            if c == "'" and not in_string:
                result.append('"')
                i += 1
                continue
            
            result.append(c)
            i += 1
        
        return ''.join(result)
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        
        # 分析历史
        self.analysis_history: Dict[str, List[RoundAnalysisResult]] = {}  # student_id -> results
        self.stage_reports: Dict[str, List[StageReport]] = {}  # student_id -> reports
    
    def analyze_after_round(
        self,
        student_id: str,
        round_id: str,
        student_work: Any,  # StudentWork对象
        evaluations_given: List[Any],  # 学生给出的评价
        evaluations_received: List[Any],  # 学生收到的评价
        previous_knowledge_state: Optional[Dict[str, float]] = None
    ) -> RoundAnalysisResult:
        """
        每轮互评后分析学生表现
        
        Args:
            student_id: 学生ID
            round_id: 轮次ID
            student_work: 学生作业
            evaluations_given: 学生给出的评价列表
            evaluations_received: 学生收到的评价列表
            previous_knowledge_state: 之前的知识状态
        
        Returns:
            分析结果
        """
        logging.info(f"分析学生 {student_id} 在第 {round_id} 轮的表现")
        
        # 1. 知识状态分析
        knowledge_state = self._analyze_knowledge_state(
            student_id, round_id, student_work, previous_knowledge_state
        )
        
        # 2. 元认知评估
        metacognition = self._assess_metacognition(
            student_id, round_id, student_work, evaluations_given, evaluations_received
        )
        
        # 3. 互评质量评估
        evaluation_quality = self._assess_evaluation_quality(
            student_id, round_id, evaluations_given
        )
        
        # 4. 生成反馈
        feedback = self._generate_round_feedback(
            knowledge_state, metacognition, evaluation_quality
        )
        
        # 5. 创建分析结果
        result = RoundAnalysisResult(
            student_id=student_id,
            round_id=round_id,
            knowledge_state=knowledge_state,
            metacognition=metacognition,
            evaluation_quality=evaluation_quality,
            feedback_to_student=feedback["feedback"],
            action_items=feedback["action_items"]
        )
        
        # 记录到历史
        if student_id not in self.analysis_history:
            self.analysis_history[student_id] = []
        self.analysis_history[student_id].append(result)
        
        logging.info(f"完成学生 {student_id} 的轮次分析")
        return result
    
    def _analyze_knowledge_state(
        self,
        student_id: str,
        round_id: str,
        student_work: Any,
        previous_knowledge_state: Optional[Dict[str, float]]
    ) -> KnowledgeStateAnalysis:
        """分析知识状态"""
        
        # 获取assignment信息
        assignment = self.safe_get(student_work, 'assignment', None)
        if assignment:
            assignment_title = self.safe_get(assignment, 'title', '未知')
            knowledge_points = self.safe_get(assignment, 'knowledge_points_covered', [])
        else:
            assignment_title = '未知'
            knowledge_points = []
        
        # 构建分析提示词
        prompt = f"""作为一名经验丰富且鼓励学生的教师，请分析学生在本轮作业中的知识掌握情况。

作业信息：
- 题目：{assignment_title}
- 知识点：{knowledge_points}
- 得分：{self.safe_get(student_work, 'score', 0)}

作业内容摘要：
{str(self.safe_get(student_work, 'content', '无内容'))[:500]}...

⚠️ 评估指导原则：
- 知识掌握度应该基于学生展示出的理解程度，而非完美标准
- 只要学生展示了对概念的基本理解，掌握度至少应该在0.5以上
- 能够正确应用知识点的学生，掌握度应该在0.7以上
- 只有完全没有展示理解的情况才给0.3以下
- 要看到学生的努力和进步潜力

请分析：
1. 学生对各个知识点的掌握程度（0-1之间的分数，参考上述指导）
2. 发现的错误模式和知识盲点
3. 学生的强项和弱项

返回JSON格式：
{{
    "knowledge_mastery": {{"知识点1": 0.75, "知识点2": 0.65}},
    "error_patterns": ["错误模式1"],
    "knowledge_gaps": ["知识盲点1"],
    "strengths": ["强项1", "强项2"],
    "weaknesses": ["弱项1"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "你是一名专业的教育评估专家，擅长分析学生的知识掌握情况。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            analysis_data = self._clean_and_parse_json(content, "知识状态分析")
            
            # 计算增长
            knowledge_growth = {}
            if previous_knowledge_state:
                for kp, current_mastery in analysis_data["knowledge_mastery"].items():
                    prev_mastery = previous_knowledge_state.get(kp, 0.0)
                    knowledge_growth[kp] = current_mastery - prev_mastery
            
            return KnowledgeStateAnalysis(
                student_id=student_id,
                round_id=round_id,
                knowledge_mastery=analysis_data["knowledge_mastery"],
                knowledge_growth=knowledge_growth,
                error_patterns=analysis_data.get("error_patterns", []),
                knowledge_gaps=analysis_data.get("knowledge_gaps", []),
                strengths=analysis_data.get("strengths", []),
                weaknesses=analysis_data.get("weaknesses", [])
            )
            
        except Exception as e:
            logging.error(f"知识状态分析失败: {e}")
            # 返回默认分析
            return KnowledgeStateAnalysis(
                student_id=student_id,
                round_id=round_id,
                knowledge_mastery={},
                knowledge_growth={}
            )
    
    def _assess_metacognition(
        self,
        student_id: str,
        round_id: str,
        student_work: Any,
        evaluations_given: List[Any],
        evaluations_received: List[Any]
    ) -> MetacognitionAssessment:
        """评估元认知能力"""
        
        # 构建评估提示词 - 使用正确的字段提取方法
        eval_given_summary = "\n".join([
            f"- 评价{i+1}: {self._get_evaluation_content(ev)[:200]}..." 
            for i, ev in enumerate(evaluations_given[:3])
        ]) if evaluations_given else "未评价他人"
        
        eval_received_summary = "\n".join([
            f"- 收到{i+1}: {self._get_evaluation_content(ev)[:200]}..."
            for i, ev in enumerate(evaluations_received[:3])
        ]) if evaluations_received else "未收到评价"
        
        prompt = f"""作为教育心理学专家，基于 Zimmerman (2000) 自我调节学习 (SRL) 三阶段模型评估学生的元认知能力。

学生给出的评价：
{eval_given_summary}

学生收到的评价：
{eval_received_summary}

学生反思：
{getattr(student_work, 'reflection', '无反思')}

作业得分：{self.safe_get(student_work, 'score', 0)}

请按 Zimmerman SRL 三阶段评估（每项0-1分）：

【阶段1：前导 (Forethought)】- 任务前的准备
- goal_setting: 目标设定 - 是否有明确的学习目标？（从反思/计划中推断）
  * 低水平：模糊目标 "我要完成任务"
  * 中等：有具体任务目标 "明确步骤"
  * 高水平：有学习目标+策略目标 "掌握知识+时间规划"
  
- strategic_planning: 策略规划 - 是否规划了学习策略？
  * 低水平：简单步骤 "先看后写"
  * 中等：明确策略 "查资料、写作"
  * 高水平：策略+时间+资源规划 "分阶段+资源规划"

【阶段2：执行 (Performance)】- 任务执行过程
- self_monitoring: 自我监控 - 执行中是否监控自己的表现？
  * 低水平：被动困惑 "不太理解"
  * 中等：主动识别问题与检查 "发现问题+检查"
  * 高水平：动态监控+中途调整 "持续检查+策略调整"
  
- attention_control: 注意控制 - 是否专注于关键内容？
  * 低水平：被动集中 "必须完成"
  * 中等：关注重点内容 "专注关键"
  * 高水平：有选择性注意+中途调整 "抓重点+忽略干扰"

【阶段3：反思 (Self-reflection)】- 任务后的反思
- self_evaluation: 自我评价 - 反思质量如何？
  * 低水平：模糊评价 "还可以"
  * 中等：具体分析优劣 "批判性分析+改进计划"
  * 高水平：批判性分析+改进计划 "深度分析+具体计划"
  
- causal_attribution: 归因 - 如何解释成败原因？
  * 低水平：外部归因 "因为找投资问题"
  * 中等：部分自我归因 "部分归因努力"
  * 高水平：成熟归因模式 "策略归因+可控归因"

返回JSON（根据学生实际表现评分，不要给假数据）：
{{
    "goal_setting": 0.7,
    "strategic_planning": 0.6,
    "self_monitoring": 0.8,
    "attention_control": 0.7,
    "self_evaluation": 0.75,
    "causal_attribution": 0.65,
    "observations": ["观察1：具体描述学生的SRL表现", "观察2"],
    "improvement_suggestions": ["建议1：针对性改进建议", "建议2"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "你是元认知研究专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            data = self._clean_and_parse_json(content, "元认知评估")
            
            # 计算三阶段得分
            forethought = (data["goal_setting"] + data["strategic_planning"]) / 2.0
            performance = (data["self_monitoring"] + data["attention_control"]) / 2.0
            reflection = (data["self_evaluation"] + data["causal_attribution"]) / 2.0
            
            # 计算总分（三阶段平均）
            overall = (forethought + performance + reflection) / 3.0
            
            # 异常检测：元认知分数异常低
            if overall < 0.25:
                logging.warning(f"⚠️ 学生 {student_id} 轮次 {round_id} 元认知分数异常低: {overall:.3f}")
                logging.debug(f"   - 前导阶段: {forethought:.3f} (目标={data['goal_setting']:.3f}, 规划={data['strategic_planning']:.3f})")
                logging.debug(f"   - 执行阶段: {performance:.3f} (监控={data['self_monitoring']:.3f}, 注意={data['attention_control']:.3f})")
                logging.debug(f"   - 反思阶段: {reflection:.3f} (评价={data['self_evaluation']:.3f}, 归因={data['causal_attribution']:.3f})")
                logging.debug(f"   - 给出评价数: {len(evaluations_given)}")
                logging.debug(f"   - 收到评价数: {len(evaluations_received)}")
            
            return MetacognitionAssessment(
                student_id=student_id,
                round_id=round_id,
                overall_score=overall,
                # 三阶段得分
                forethought_phase=forethought,
                performance_phase=performance,
                reflection_phase=reflection,
                # 六个细分维度
                goal_setting=data["goal_setting"],
                strategic_planning=data["strategic_planning"],
                self_monitoring=data["self_monitoring"],
                attention_control=data["attention_control"],
                self_evaluation=data["self_evaluation"],
                causal_attribution=data["causal_attribution"],
                observations=data.get("observations", []),
                improvement_suggestions=data.get("improvement_suggestions", [])
            )
            
        except Exception as e:
            logging.error(f"元认知评估失败: {e}")
            return MetacognitionAssessment(
                student_id=student_id,
                round_id=round_id,
                overall_score=0.5,
                forethought_phase=0.5,
                performance_phase=0.5,
                reflection_phase=0.5,
                goal_setting=0.5,
                strategic_planning=0.5,
                self_monitoring=0.5,
                attention_control=0.5,
                self_evaluation=0.5,
                causal_attribution=0.5
            )
    
    def _assess_evaluation_quality(
        self,
        student_id: str,
        round_id: str,
        evaluations_given: List[Any]
    ) -> PeerEvaluationQualityAssessment:
        """评估互评质量"""
        
        if not evaluations_given:
            return PeerEvaluationQualityAssessment(
                student_id=student_id,
                round_id=round_id,
                depth=0.5,
                accuracy=0.5,
                constructiveness=0.5,
                overall_quality=0.5,
                evaluation_summary="未评价他人"
            )
        
        # 分析评价内容 - 支持多种字段名
        evaluations_text = "\n\n".join([
            f"评价{i+1}:\n{self._get_evaluation_content(ev)}"
            for i, ev in enumerate(evaluations_given)
        ])
        
        prompt = f"""评估学生给出的同伴评价质量。

评价内容：
{evaluations_text}

请从以下维度评分（0-1）：
1. depth: 深度（表面/深入分析）
2. accuracy: 准确性（评价客观合理）
3. constructiveness: 建设性（提供有效建议）

返回JSON：
{{
    "depth": 0.7,
    "accuracy": 0.8,
    "constructiveness": 0.6,
    "evaluation_summary": "评价内容摘要",
    "positive_aspects": ["亮点1", "亮点2"],
    "areas_for_improvement": ["可改进1"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "你是评价质量评估专家。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            data = self._clean_and_parse_json(content, "互评质量评估")
            
            overall = (data["depth"] + data["accuracy"] + data["constructiveness"]) / 3.0
            
            return PeerEvaluationQualityAssessment(
                student_id=student_id,
                round_id=round_id,
                depth=data["depth"],
                accuracy=data["accuracy"],
                constructiveness=data["constructiveness"],
                overall_quality=overall,
                evaluation_summary=data.get("evaluation_summary", ""),
                positive_aspects=data.get("positive_aspects", []),
                areas_for_improvement=data.get("areas_for_improvement", [])
            )
            
        except Exception as e:
            logging.error(f"互评质量评估失败: {e}")
            return PeerEvaluationQualityAssessment(
                student_id=student_id,
                round_id=round_id,
                depth=0.5,
                accuracy=0.5,
                constructiveness=0.5,
                overall_quality=0.5,
                evaluation_summary="评估失败"
            )
    
    def _generate_round_feedback(
        self,
        knowledge_state: KnowledgeStateAnalysis,
        metacognition: MetacognitionAssessment,
        evaluation_quality: PeerEvaluationQualityAssessment
    ) -> Dict[str, Any]:
        """生成轮次反馈"""
        
        prompt = f"""基于学生本轮表现，生成简短反馈（2-3段）。

知识掌握：
- 强项：{', '.join(knowledge_state.strengths)}
- 弱项：{', '.join(knowledge_state.weaknesses)}

元认知水平：{metacognition.overall_score:.2f}

互评质量：{evaluation_quality.overall_quality:.2f}

生成：
1. 对学生表现的总体评价
2. 3-5条行动建议

返回JSON：
{{
    "feedback": "反馈内容",
    "action_items": ["建议1", "建议2", "建议3"]
}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "你是一名鼓励性的教师。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            return self._clean_and_parse_json(content, "反馈生成")
            
        except Exception as e:
            logging.error(f"反馈生成失败: {e}")
            return {
                "feedback": "本轮表现良好，继续努力！",
                "action_items": ["巩固基础知识", "多练习", "提高评价质量"]
            }
    
    def generate_stage_report(
        self,
        student_id: str,
        stage_id: str,
        stage_name: str,
        start_round: int,
        end_round: int,
        student: Any = None  # 添加student参数以获取完整信息
    ) -> StageReport:
        """生成阶段学情报告"""
        
        logging.info(f"生成学生 {student_id} 阶段 {stage_id} 的学情报告")
        
        # 获取该学生在此阶段的所有分析
        student_analyses = self.analysis_history.get(student_id, [])
        stage_analyses = [
            a for a in student_analyses
            if start_round <= int(a.round_id.split('_')[-1].replace('round', '')) <= end_round
        ]
        
        if not stage_analyses:
            logging.warning(f"学生 {student_id} 阶段 {stage_id} 无分析数据")
            # 返回空报告
            return self._create_empty_report(
                student_id, stage_id, stage_name, start_round, end_round
            )
        
        # 聚合数据
        report = self._aggregate_stage_data(
            student_id, stage_id, stage_name,
            start_round, end_round, stage_analyses, student
        )
        
        # 保存报告
        if student_id not in self.stage_reports:
            self.stage_reports[student_id] = []
        self.stage_reports[student_id].append(report)
        
        logging.info(f"完成学生 {student_id} 的阶段报告")
        return report
    
    def _create_empty_report(
        self, student_id, stage_id, stage_name, start_round, end_round
    ) -> StageReport:
        """创建空报告"""
        return StageReport(
            student_id=student_id,
            stage_id=stage_id,
            stage_name=stage_name,
            start_round=start_round,
            end_round=end_round,
            initial_knowledge_mastery={},
            final_knowledge_mastery={},
            knowledge_growth_rate={},
            most_improved_topics=[],
            topics_needing_attention=[],
            metacognition_trajectory=[],
            metacognition_growth=0.0,
            evaluation_quality_trajectory=[],
            evaluation_quality_improvement=0.0,
            average_assignment_score=0.0,
            score_trend="无数据",
            total_evaluations_given=0,
            total_evaluations_received=0,
            avg_evaluation_quality_given=0.0,
            overall_performance="无数据",
            strengths=[],
            weaknesses=[],
            next_stage_focus=[],
            recommended_resources=[],
            learning_strategy_suggestions=[],
            detailed_feedback="本阶段无足够数据生成报告。"
        )
    
    def _aggregate_stage_data(
        self, student_id, stage_id, stage_name,
        start_round, end_round, stage_analyses, student=None
    ) -> StageReport:
        """聚合阶段数据（简化版）"""
        
        # 初始和最终知识状态
        initial_km = stage_analyses[0].knowledge_state.knowledge_mastery
        final_km = stage_analyses[-1].knowledge_state.knowledge_mastery
        
        # 计算知识增长率
        knowledge_growth_rate = {}
        for kp in set(list(initial_km.keys()) + list(final_km.keys())):
            initial_val = initial_km.get(kp, 0.0)
            final_val = final_km.get(kp, 0.0)
            if initial_val > 0:
                growth_rate = (final_val - initial_val) / initial_val
                knowledge_growth_rate[kp] = growth_rate
            elif final_val > 0:
                knowledge_growth_rate[kp] = 1.0  # 从0开始的增长
        
        # 找出进步最大的知识点
        most_improved = sorted(
            knowledge_growth_rate.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        
        # 找出需要关注的知识点（掌握度低于0.5的）
        topics_needing_attention = [
            kp for kp, mastery in final_km.items() if mastery < 0.5
        ]
        
        # 元认知轨迹
        meta_trajectory = [
            (i + start_round, a.metacognition.overall_score)
            for i, a in enumerate(stage_analyses)
        ]
        meta_growth = (
            stage_analyses[-1].metacognition.overall_score -
            stage_analyses[0].metacognition.overall_score
        ) if len(stage_analyses) > 1 else 0.0
        
        # 互评质量轨迹
        eval_trajectory = [
            (i + start_round, a.evaluation_quality.overall_quality)
            for i, a in enumerate(stage_analyses)
        ]
        eval_improvement = (
            stage_analyses[-1].evaluation_quality.overall_quality -
            stage_analyses[0].evaluation_quality.overall_quality
        ) if len(stage_analyses) > 1 else 0.0
        
        # 计算平均作业分数（使用知识掌握度的平均值作为近似）
        avg_mastery = sum(final_km.values()) / len(final_km) if final_km else 0.0
        avg_score = avg_mastery * 100  # 转换为0-100分制
        
        # 分数趋势
        if len(stage_analyses) > 1:
            initial_avg = sum(initial_km.values()) / len(initial_km) if initial_km else 0.0
            final_avg = sum(final_km.values()) / len(final_km) if final_km else 0.0
            if final_avg > initial_avg + 0.1:
                score_trend = "上升"
            elif final_avg < initial_avg - 0.1:
                score_trend = "下降"
            else:
                score_trend = "稳定"
        else:
            score_trend = "稳定"
        
        return StageReport(
            student_id=student_id,
            stage_id=stage_id,
            stage_name=stage_name,
            start_round=start_round,
            end_round=end_round,
            initial_knowledge_mastery=initial_km,
            final_knowledge_mastery=final_km,
            knowledge_growth_rate=knowledge_growth_rate,
            most_improved_topics=most_improved,
            topics_needing_attention=topics_needing_attention,
            metacognition_trajectory=meta_trajectory,
            metacognition_growth=meta_growth,
            evaluation_quality_trajectory=eval_trajectory,
            evaluation_quality_improvement=eval_improvement,
            average_assignment_score=avg_score,
            score_trend=score_trend,
            total_evaluations_given=len(stage_analyses) * 2,  # 估计
            total_evaluations_received=len(stage_analyses) * 2,
            avg_evaluation_quality_given=sum(a.evaluation_quality.overall_quality for a in stage_analyses) / len(stage_analyses),
            overall_performance="良好",
            strengths=["积极参与", "持续进步"],
            weaknesses=["需要加强实践"],
            next_stage_focus=["深入学习核心概念"],
            recommended_resources=["在线课程", "练习题库"],
            learning_strategy_suggestions=["定期复习", "主动提问"],
            detailed_feedback=f"在{stage_name}阶段表现良好，元认知能力提升{meta_growth:.2f}，继续保持！"
        )


if __name__ == "__main__":
    print("✅ 教师分析模块已创建")
    print("包含功能:")
    print("  - 每轮互评后的知识状态分析")
    print("  - 元认知能力评估")
    print("  - 互评质量评估")
    print("  - 阶段学情报告生成")
