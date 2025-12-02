from typing import Dict, Any, List, Optional
import openai
from models.data_models import Student, StudentWork, Assignment, Course, KnowledgePoint
from models.psychology_models import StudentPsychology
from memory import MemoryContext, LearningOutcome
from memory.enhanced_memory import create_enhanced_memory_system
from memory.new_memory_system import NewMemorySystem
from memory.new_memory_models import (
    LearningMemory,
    PeerEvaluationMemory,
    ReceivedEvaluationMemory,
    MemoryDimension
)
from config.settings import Config
from config.peer_review_config import PeerReviewConfig
import random
import json
import logging
import os
import shutil
from datetime import datetime
import uuid

class StudentAgent:
    """升级的学生代理，集成新一代三维记忆系统和心理状态系统"""
    
    def __init__(self, student: Student, memory_config: Dict[str, Any] = None, peer_review_config: Optional[PeerReviewConfig] = None):
        self.student = student
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        
        # 互评配置
        self.peer_review_config = peer_review_config or PeerReviewConfig()
        
        # 初始化心理状态系统
        self.psychology = self._load_psychology_state()
        
        # 初始化新一代记忆系统（三维记忆结构 + 温度参数检索）
        self.new_memory_system = NewMemorySystem(
            student_id=student.id,
            use_semantic=memory_config.get("use_semantic_retrieval", True) if memory_config else True
        )
        
        # 保留旧记忆系统以兼容现有代码（标记为deprecated）
        default_config = {
            "use_semantic_retrieval": True,
            "enable_experience_replay": True,
            "enable_quality_control": True
        }
        default_config.update(memory_config or {})
        
        self.memory_system = create_enhanced_memory_system(
            student_id=student.id,
            config=default_config
        )
        
        # 使用新记忆系统的标志
        self.use_new_memory = memory_config.get("use_new_memory", True) if memory_config else True
        
        # 【新增】初始化元认知调节器
        from tools.metacognitive_regulator import create_regulator_for_student
        self.metacognitive_regulator = create_regulator_for_student(student.id)
        logging.info(f"元认知调节器已为学生 {student.name} 创建")
        
        # 性能跟踪
        self.performance_metrics = {
            "assignments_completed": 0,
            "average_performance": 0.0,
            "memory_usage_frequency": 0,
            "learning_effectiveness": 0.0,
            "current_round": 0,  # 【新增】当前轮次
            "total_evaluations": 0,  # 【新增】总评价次数
            "recent_scores": []  # 【新增】最近分数列表
        }
        
        # 【新增】追踪上一次分数（用于计算学习增益）
        self.last_assignment_score = 0.5
        
        logging.info(f"学生Agent初始化: {student.name}, 使用新记忆系统: {self.use_new_memory}, 心理状态已加载")
    
    def _load_psychology_state(self) -> StudentPsychology:
        """加载或创建心理状态"""
        if self.student.psychology_state:
            try:
                return StudentPsychology.from_dict(self.student.psychology_state)
            except:
                pass
        # 根据学生类型创建默认心理状态
        return StudentPsychology.create_default(self.student.student_type.value)
    
    def _save_psychology_state(self):
        """保存心理状态到学生模型"""
        self.student.psychology_state = self.psychology.to_dict()
    
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
            if other_id == self.student.id:
                continue  # 跳过自己
            
            # 如果已经有关系记录，不覆盖（可能是从存档加载的）
            if other_id in self.psychology.social.relationships:
                continue
            
            # 根据概率随机生成初始关系
            rand = random.random()
            
            if rand < 0.08:  # 8%概率是好朋友
                relationship = random.uniform(0.4, 0.8)
                logging.debug(f"初始化好友关系: {self.student.name} -> {other_id[:8]}... = {relationship:.2f}")
            elif rand < 0.13:  # 5%概率是不太对付的人
                relationship = random.uniform(-0.6, -0.2)
                logging.debug(f"初始化敌对关系: {self.student.name} -> {other_id[:8]}... = {relationship:.2f}")
            elif rand < 0.25:  # 12%概率是普通认识
                relationship = random.uniform(0.1, 0.3)
            else:  # 75%概率是陌生人
                relationship = 0.0
            
            if relationship != 0.0:
                self.psychology.social.relationships[other_id] = relationship
        
        # 保存更新后的心理状态
        self._save_psychology_state()
        
        # 统计初始化结果
        friends = sum(1 for v in self.psychology.social.relationships.values() if v > 0.3)
        enemies = sum(1 for v in self.psychology.social.relationships.values() if v < -0.1)
        acquaintances = len(self.psychology.social.relationships) - friends - enemies
        
        logging.info(f"社交关系初始化完成 - {self.student.name}: {friends}个朋友, {acquaintances}个熟人, {enemies}个不合的人")
    
    def complete_assignment(self, assignment: Assignment, course: Optional['Course'] = None) -> StudentWork:
        """使用智能记忆系统完成作业"""
        logging.info(f"开始完成作业 - 学生: {self.student.name}, 作业: {assignment.title}")
        logging.info(f"心理状态 - 动力: {self.psychology.emotion.motivation:.2f}, 疲劳: {self.psychology.emotion.fatigue:.2f}")
        start_time = datetime.now()
        
        # 根据心理状态调整行为
        motivation_factor = self._get_motivation_factor()
        logging.info(f"动力因子: {motivation_factor:.2f}")
        
        # 【新增】使用元认知调节器调节记忆检索权重
        adjusted_weights = self._regulate_memory_weights(assignment, course)
        logging.info(f"记忆权重已调节: {adjusted_weights}")
        
        # 构建记忆上下文
        logging.info(f"构建记忆上下文 - 学生: {self.student.name}")
        memory_context = self._build_memory_context(assignment, course)
        
        # 检索相关经验案例
        logging.info(f"检索相关经验案例 - 学生: {self.student.name}")
        
        # 如果使用新记忆系统，从新系统检索
        if self.use_new_memory:
            # 构建查询
            query = f"{assignment.title}: {assignment.description}"
            
            # 从新记忆系统检索相关记忆
            new_retrieval_result = self.new_memory_system.retrieve(
                query=query,
                dimension_filter=[
                    MemoryDimension.LEARNING,
                    MemoryDimension.PEER_EVALUATION,
                    MemoryDimension.RECEIVED_EVALUATION
                ],
                top_k=5
            )
            
            # 转换为旧格式以兼容现有代码
            retrieval_result = self._convert_new_to_old_retrieval(new_retrieval_result, memory_context)
            logging.info(f"从新记忆系统检索到 {len(new_retrieval_result.retrieved_memories)} 条记忆")
        else:
            # 使用旧系统（向后兼容）
            retrieval_result = self.memory_system.retrieve_relevant_cases(
                current_problem=f"{assignment.title}: {assignment.description}",
                context=memory_context,
                max_cases=3
            )
        
        # 触发增强版经验回放（结合检索结果）
        logging.info(f"触发增强版经验回放 - 学生: {self.student.name}")
        replay_result = self.memory_system.trigger_experience_replay_enhanced(
            learning_context=memory_context,
            replay_strategy="contextual"
        )
        
        # 获取学习建议
        logging.info(f"获取学习建议 - 学生: {self.student.name}")
        recommendations = self.memory_system.get_learning_recommendations(memory_context)
        
        # 构建智能提示词
        logging.info(f"构建智能提示词 - 学生: {self.student.name}")
        prompt = self._build_intelligent_prompt(
            assignment, 
            memory_context,
            retrieval_result,
            recommendations
        )
        
        # 调用LLM生成作业内容
        logging.info(f"调用LLM生成作业内容 - 学生: {self.student.name}")
        response = self.client.chat.completions.create(
            model=Config.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": self._get_enhanced_system_prompt(assignment)},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        content = response.choices[0].message.content
        
        # 创建学生作品
        logging.info(f"创建学生作品 - 学生: {self.student.name}")
        work = self._create_student_work(assignment, content)
        
        # 评估学习结果
        logging.info(f"开始评估学习结果 - 学生: {self.student.name}")
        learning_outcome = self._evaluate_learning_outcome(
            work, assignment, start_time, retrieval_result
        )
        logging.info(f"学习结果评估完成 - 学生: {self.student.name}, 成功: {learning_outcome.success}")
        
        # 存储学习经验到记忆系统
        logging.info(f"准备存储学习经验 - 学生: {self.student.name}")
        try:
            self.memory_system.store_learning_experience(
                problem=f"{assignment.title}: {assignment.description}",
                solution=work.content,
                context=memory_context,
                outcome=learning_outcome
            )
            logging.info(f"学习经验存储成功 - 学生: {self.student.name}")
        except Exception as e:
            logging.error(f"学习经验存储失败 - 学生: {self.student.name}, 错误: {e}")
            import traceback
            logging.error(f"详细错误: {traceback.format_exc()}")
            # 不阻止作业完成，只记录错误
        
        # 更新性能指标
        self._update_performance_metrics(learning_outcome, retrieval_result)
        
        # 【新增】提供反馈给元认知调节器
        assignment_score = learning_outcome.score / 100.0  # 归一化到0-1
        evaluation_quality = 0.7  # 默认评价质量（可以根据作业完成情况估计）
        if learning_outcome.success:
            evaluation_quality = 0.8
        self._update_regulator_with_feedback(assignment_score, evaluation_quality)
        
        # 更新传统记忆系统（保持兼容性）
        self._update_legacy_memory(assignment, work, course)
        
        # 使用新记忆系统存储学习记忆
        if self.use_new_memory:
            self._store_to_new_memory_system(assignment, work, learning_outcome, retrieval_result)
        
        # 更新心理状态
        self._update_psychology_after_assignment(learning_outcome)
        self._save_psychology_state()
        
        logging.info(f"Assignment completed by {self.student.name} using intelligent memory system")
        
        return work
    
    def _get_motivation_factor(self) -> float:
        """根据心理状态计算动力因子，影响作业质量"""
        mood = self.psychology.emotion
        
        # 基础动力
        factor = mood.motivation
        
        # 疲劳度降低效率
        factor *= (1 - mood.fatigue * 0.3)
        
        # 挫败感也会降低效率
        factor *= (1 - mood.frustration * 0.2)
        
        # 信心影响愿意尝试的程度
        factor *= (0.7 + mood.confidence * 0.3)
        
        return max(0.3, min(1.0, factor))
    
    def _update_psychology_after_assignment(self, learning_outcome):
        """作业完成后更新心理状态"""
        success = learning_outcome.success if hasattr(learning_outcome, 'success') else False
        score = learning_outcome.score / 100.0 if hasattr(learning_outcome, 'score') else 0.5
        
        if success and score > 0.7:
            # 成功完成，增加动力和信心
            experience = {
                'type': 'assignment_success',
                'impact': score - 0.5,  # 高分正向影响
                'description': f'成功完成作业，得分{score:.0%}'
            }
            self.psychology.emotion.mood_history.append(experience)
            self.psychology.emotion.motivation = min(1.0, self.psychology.emotion.motivation + 0.05)
            self.psychology.emotion.confidence = min(1.0, self.psychology.emotion.confidence + 0.03)
            self.psychology.emotion.frustration = max(0, self.psychology.emotion.frustration - 0.05)
        elif score < 0.5:
            # 表现不佳，可能增加挫败感
            experience = {
                'type': 'assignment_struggle',
                'impact': score - 0.5,
                'description': f'作业完成困难，得分{score:.0%}'
            }
            self.psychology.emotion.mood_history.append(experience)
            self.psychology.emotion.frustration = min(1.0, self.psychology.emotion.frustration + 0.1)
            self.psychology.emotion.motivation = max(0.2, self.psychology.emotion.motivation - 0.05)
        
        # 完成作业会增加疲劳
        self.psychology.emotion.fatigue = min(1.0, self.psychology.emotion.fatigue + 0.1)
        
        # 保持最近经历列表在合理范围
        self.psychology.emotion.mood_history = self.psychology.emotion.mood_history[-10:]
    
    def _update_psychology_after_feedback(self, evaluation_data: Dict[str, Any], evaluator_id: str, agreement: float):
        """收到评价反馈后更新心理状态"""
        score = evaluation_data.get("score", 70)
        
        # 调用心理模型的情绪更新方法
        self.psychology.update_mood_after_feedback(
            feedback_score=score / 100.0,
            is_positive=(score >= 70)
        )
        
        # 更新与评价者的社交关系
        if score >= 80:
            # 高分评价增进关系
            current = self.psychology.social.relationships.get(evaluator_id, 0.0)
            self.psychology.social.relationships[evaluator_id] = min(1.0, current + 0.1)
        elif score < 60:
            # 低分评价可能降低好感（取决于认同度）
            if agreement < 0.5:  # 不认同低分评价
                current = self.psychology.social.relationships.get(evaluator_id, 0.0)
                self.psychology.social.relationships[evaluator_id] = max(-1.0, current - 0.15)
        
        # 记录这次收到评价的经历到情绪历史
        self.psychology.emotion.mood_history.append({
            'type': 'received_feedback',
            'impact': (score - 70) / 100.0,  # 70分为中点
            'description': f'收到{evaluator_id[:8]}的评价: {score}分',
            'evaluator_id': evaluator_id
        })
        
        logging.info(f"心理状态更新 - 收到{score}分评价, 动力: {self.psychology.emotion.motivation:.2f}, 信心: {self.psychology.emotion.confidence:.2f}")
    
    def _build_memory_context(self, assignment: Assignment, course: Optional['Course']) -> MemoryContext:
        """构建记忆上下文"""
        return MemoryContext(
            knowledge_point_ids=assignment.knowledge_points_covered,
            difficulty_level=assignment.difficulty_level,
            current_problem=f"{assignment.title}: {assignment.description}",
            available_resources=["course_materials", "previous_assignments"],
            time_constraints=assignment.estimated_hours * 60,  # 转换为分钟
            learning_objectives=assignment.requirements if hasattr(assignment, 'requirements') else []
        )
    
    def _build_intelligent_prompt(self, 
                                 assignment: Assignment,
                                 memory_context: MemoryContext,
                                 retrieval_result,
                                 recommendations: List[Dict[str, Any]]) -> str:
        """构建智能提示词"""
        
        base_prompt = self._build_assignment_prompt(assignment)
        
        # 添加记忆检索结果
        memory_prompt = "\n\n=== 你的学习经验和相关案例 ===\n"
        
        if retrieval_result.retrieved_cases:
            memory_prompt += f"检索到 {len(retrieval_result.retrieved_cases)} 个相关经验案例（置信度: {retrieval_result.confidence_level:.2f}）：\n"
            memory_prompt += retrieval_result.explanation + "\n\n"
            
            for i, case in enumerate(retrieval_result.retrieved_cases[:2], 1):  # 限制显示案例数量
                similarity = retrieval_result.similarity_scores[i-1] if i-1 < len(retrieval_result.similarity_scores) else 0.0
                memory_prompt += f"案例 {i} (相似度: {similarity:.2f}):\n"
                memory_prompt += f"问题: {case.get('problem_description', '无描述')}\n"
                memory_prompt += f"解决方案: {case.get('solution', '无解决方案')[:200]}...\n"
                memory_prompt += f"成功率: {case.get('success_score', 0.0):.2f}\n\n"
        else:
            memory_prompt += "没有找到直接相关的经验案例，需要依靠基础知识和推理能力。\n\n"
        
        # 添加学习建议
        if recommendations:
            memory_prompt += "=== 学习建议 ===\n"
            for rec in recommendations:
                if rec["type"] == "concept_reinforcement":
                    memory_prompt += f"- 注意加强 {rec['concept']} 概念的理解（当前掌握度: {rec['mastery_level']:.2f}）\n"
                elif rec["type"] == "review_session":
                    memory_prompt += f"- {rec['description']}\n"
                elif rec["type"] == "concept_expansion":
                    memory_prompt += f"- 可以拓展学习相关概念: {', '.join(rec.get('related_concepts', []))}\n"
        
        # 添加概念掌握情况
        memory_prompt += "\n=== 你的知识掌握情况 ===\n"
        concept_mastery = self.memory_system.memory_state.concept_mastery
        for concept in memory_context.knowledge_point_ids:
            mastery = concept_mastery.get(concept, 0.0)
            mastery_desc = self._get_mastery_description(mastery)
            memory_prompt += f"- {concept}: {mastery_desc} ({mastery:.2f})\n"
        
        # 根据学生类型的记忆策略
        memory_strategy = self._get_intelligent_memory_strategy(retrieval_result.confidence_level)
        memory_prompt += f"\n=== 建议的学习策略 ===\n{memory_strategy}\n"
        
        return base_prompt + memory_prompt
    
    def _get_intelligent_memory_strategy(self, confidence_level: float) -> str:
        """获取智能记忆策略"""
        base_strategy = self._get_memory_strategy()  # 保留原有策略
        
        if confidence_level > 0.7:
            strategy_addition = "你有很好的相关经验可以参考，充分利用这些成功案例来指导当前的工作。"
        elif confidence_level > 0.4:
            strategy_addition = "你有一些相关经验可以参考，但要结合当前的具体情况进行调整。"
        else:
            strategy_addition = "相关经验较少，主要依靠基础知识和逻辑推理来解决问题。"
        
        return f"{base_strategy}\n\n记忆系统建议：{strategy_addition}"
    
    def _evaluate_learning_outcome(self, 
                                  work: StudentWork,
                                  assignment: Assignment,
                                  start_time: datetime,
                                  retrieval_result) -> LearningOutcome:
        """评估学习结果"""
        
        # 估算成功度
        estimated_performance = self._estimate_assignment_performance(work, assignment)
        success = estimated_performance > 0.5  # 降低成功标准，增加成功率
        
        # 计算花费时间 - 基于难度和学生类型的合理估算
        base_time = 60  # 基准时间60分钟
        
        # 根据难度调整时间
        difficulty_multiplier = 0.5 + assignment.difficulty_level * 0.3  # 0.8-2.0倍
        
        # 根据学生类型调整时间
        type_time_factors = {
            "excellent": 0.7,    # 优秀学生用时较少
            "good": 0.9,
            "average": 1.1,
            "below_average": 1.4, # 基础较差的学生用时较多
            "strict": 1.2,       # 严格的学生会花更多时间完善
            "lenient": 0.8,
            "perfunctory": 0.6   # 敷衍的学生用时最少
        }
        
        type_factor = type_time_factors.get(self.student.student_type.value, 1.0)
        
        # 考虑成功与否对时间的影响
        success_factor = 0.8 if estimated_performance > 0.6 else 1.3
        
        # 计算最终时间，添加随机性
        estimated_time = base_time * difficulty_multiplier * type_factor * success_factor
        time_spent = max(30, int(estimated_time * random.uniform(0.7, 1.3)))
        
        # 识别学到的概念
        concepts_learned = []
        concepts_reinforced = []
        
        # 基于检索结果和作业内容分析概念学习
        if retrieval_result.retrieved_cases:
            # 如果有参考案例，认为相关概念得到了强化
            concepts_reinforced = assignment.knowledge_points_covered
        else:
            # 如果没有参考案例，认为这些概念是新学习的
            concepts_learned = assignment.knowledge_points_covered
        
        # 模拟可能的错误
        errors_made = []
        if estimated_performance < 0.7:
            # 根据学生类型和难度模拟常见错误
            if assignment.difficulty_level > 3:
                errors_made.append("复杂逻辑处理不当")
            if self.student.student_type.value in ["below_average", "perfunctory"]:
                errors_made.append("基础概念理解不足")
        
        # 生成反思
        reflection = self._generate_reflection(estimated_performance, retrieval_result, assignment)
        
        return LearningOutcome(
            success=success,
            score=estimated_performance * 100,
            concepts_learned=concepts_learned,
            concepts_reinforced=concepts_reinforced,
            errors_made=errors_made,
            time_spent=time_spent,
            reflection=reflection
        )

    def _generate_reflection(self, performance: float, retrieval_result, assignment: Assignment) -> str:
        """使用大模型生成自然的学习反思"""
        
        # 构建反思生成的提示词
        prompt = f"""作为一名{self.student.student_type.value}水平的学生，刚完成了一次作业。请生成一段简短自然的学习反思（2-3句话）。

作业信息：
- 题目：{assignment.title}
- 涉及知识点：{', '.join(assignment.knowledge_points_covered[:3])}

完成情况：
- 预估表现分数：{performance * 100:.1f}分
- 是否使用了历史经验：{"是" if retrieval_result.retrieved_cases else "否"}

学生特点：
- 类型：{self.student.student_type.value}
- GPA：{self.student.gpa:.2f}
- 编程经验：{self.student.programming_experience}年

要求：
1. 使用第一人称，语气自然真实
2. 根据表现分数反映相应的情绪和认识
3. 如果使用了历史经验，可以提及
4. 符合学生类型的性格特点
5. 不要太过模板化，要有个性
6. 字数控制在50-100字

直接输出反思内容，不需要任何标题或前缀："""

        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "你是一个帮助生成学生学习反思的助手。生成的反思要自然、真实、有个性。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,  # 稍高的温度保证多样性
                max_tokens=200
            )
            
            reflection = response.choices[0].message.content.strip()
            return reflection
            
        except Exception as e:
            logging.warning(f"使用大模型生成反思失败，使用简化版本: {str(e)}")
            # 降级方案：简单的反思
            if performance > 0.8:
                return "这次作业完成得不错，对知识点有了更深的理解。"
            elif performance > 0.6:
                return "作业基本完成，还有一些地方需要改进。"
            elif performance > 0.4:
                return "遇到了一些困难，但也学到了新东西。"
            else:
                return "这次作业挺有挑战的，需要继续努力。"

    def _update_performance_metrics(self, learning_outcome: LearningOutcome, retrieval_result):
        """更新性能指标"""
        self.performance_metrics["assignments_completed"] += 1
        
        # 【新增】更新当前轮次
        self.performance_metrics["current_round"] += 1
        
        # 更新平均性能
        current_avg = self.performance_metrics["average_performance"]
        count = self.performance_metrics["assignments_completed"]
        new_avg = (current_avg * (count - 1) + learning_outcome.score / 100) / count
        self.performance_metrics["average_performance"] = new_avg
        
        # 更新记忆使用频率
        if retrieval_result.retrieved_cases:
            self.performance_metrics["memory_usage_frequency"] += 1
        
        # 更新学习效果
        self.performance_metrics["learning_effectiveness"] = self.memory_system.memory_state.memory_effectiveness
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        memory_stats = self.memory_system.get_memory_statistics()
        memory_stats.update(self.performance_metrics)
        return memory_stats
    
    # ==================== 元认知调节器相关方法 ====================
    
    def _regulate_memory_weights(self, assignment: Assignment, course: Optional['Course']) -> Dict[str, float]:
        """
        【新增方法】根据学习情境调节记忆检索权重
        
        使用元认知调节器动态调整记忆检索的4个权重参数：
        - weight_relevance: 相关性权重
        - weight_recency: 时新性权重
        - weight_importance: 重要性权重
        - weight_success: 成功度权重
        """
        from tools.metacognitive_regulator import regulate_memory_weights
        
        # 1. 当前掌握度（基于知识点平均掌握度）
        if hasattr(assignment, 'knowledge_points_covered') and assignment.knowledge_points_covered:
            mastery_scores = [
                self.student.knowledge_mastery.get(kp_id, 0.5)
                for kp_id in assignment.knowledge_points_covered
            ]
            current_mastery = sum(mastery_scores) / len(mastery_scores) if mastery_scores else 0.5
        else:
            current_mastery = 0.5
        
        # 2. 元认知水平（从新记忆系统获取或使用默认值）
        if hasattr(self.new_memory_system, 'memory_state') and hasattr(self.new_memory_system.memory_state, 'metacognition_history'):
            meta_history = self.new_memory_system.memory_state.metacognition_history
            if meta_history:
                metacognition_level = meta_history[-1][1]
            else:
                metacognition_level = 0.7  # 默认中等水平
        else:
            metacognition_level = 0.7
        
        # 3. 记忆状态
        stm_size = len(self.new_memory_system.stm) if hasattr(self.new_memory_system, 'stm') else 0
        ltm_size = len(self.new_memory_system.ltm) if hasattr(self.new_memory_system, 'ltm') else 0
        
        # 调用元认知调节器（使用简化的参数列表）
        adjusted_weights = regulate_memory_weights(
            regulator=self.metacognitive_regulator,
            current_mastery=current_mastery,
            metacognition_level=metacognition_level,
            stm_size=stm_size,
            ltm_size=ltm_size
        )
        
        # 应用调节后的权重到记忆检索配置
        if hasattr(self.new_memory_system, 'retrieval_config'):
            self.new_memory_system.retrieval_config.weight_relevance = adjusted_weights['relevance']
            self.new_memory_system.retrieval_config.weight_recency = adjusted_weights['recency']
            self.new_memory_system.retrieval_config.weight_importance = adjusted_weights['importance']
            self.new_memory_system.retrieval_config.weight_success = adjusted_weights['success']
            
            logging.info(f"[{self.student.name}] 权重已应用: "
                        f"相关性={adjusted_weights['relevance']:.3f}, "
                        f"时新性={adjusted_weights['recency']:.3f}, "
                        f"重要性={adjusted_weights['importance']:.3f}, "
                        f"成功度={adjusted_weights['success']:.3f}")
        
        return adjusted_weights
    
    def _calculate_avg_memory_age(self, current_round: int) -> float:
        """计算平均记忆年龄"""
        if not hasattr(self.new_memory_system, 'stm') or not hasattr(self.new_memory_system, 'ltm'):
            return 5.0  # 默认值
        
        ages = []
        
        # 计算短期记忆年龄
        for memory in self.new_memory_system.stm:
            if hasattr(memory, 'round_created'):
                ages.append(current_round - memory.round_created)
        
        # 计算长期记忆年龄
        for memory in self.new_memory_system.ltm:
            if hasattr(memory, 'round_created'):
                ages.append(current_round - memory.round_created)
        
        return sum(ages) / len(ages) if ages else 5.0
    
    def _update_regulator_with_feedback(self, assignment_score: float, evaluation_quality: float):
        """
        【新增方法】提供反馈给元认知调节器
        
        Args:
            assignment_score: 作业得分 (0-1)
            evaluation_quality: 评价质量 (0-1)
        """
        from tools.metacognitive_regulator import update_regulator
        
        # 计算学习增益
        learning_gain = max(0.0, assignment_score - self.last_assignment_score)
        
        # 更新调节器
        update_regulator(
            regulator=self.metacognitive_regulator,
            assignment_score=assignment_score,
            evaluation_quality=evaluation_quality,
            learning_gain=learning_gain
        )
        
        # 更新上一次分数
        self.last_assignment_score = assignment_score
        
        # 记录到最近分数列表
        self.performance_metrics['recent_scores'].append(assignment_score)
        if len(self.performance_metrics['recent_scores']) > 10:
            self.performance_metrics['recent_scores'] = self.performance_metrics['recent_scores'][-10:]
        
        logging.info(f"[{self.student.name}] 调节器已更新: "
                    f"分数={assignment_score:.2f}, "
                    f"质量={evaluation_quality:.2f}, "
                    f"增益={learning_gain:.2f}")
    
    # ==================== 元认知调节器相关方法结束 ====================
    
    def save_memory_state(self, base_path: str):
        """保存记忆状态"""
        # 先从Student同步short/long_term_memory到记忆系统
        self.memory_system.sync_from_student(self.student)
        
        # 保存记忆状态
        filepath = f"{base_path}/student_{self.student.id}_memory.json"
        self.memory_system.save_memory_state(filepath)
        
        # 同步长期记忆到Student模型
        self.sync_long_term_memory()
    
    def sync_long_term_memory(self):
        """将智能记忆系统中的知识向量同步到Student模型的long_term_memory字段"""
        knowledge_vectors = self.memory_system.memory_state.knowledge_vectors
        
        # 清空现有长期记忆，准备同步
        self.student.long_term_memory = {}
        
        # 同步知识点向量（只同步知识点相关的，不包含案例ID）
        for key, value in knowledge_vectors.items():
            # 过滤掉案例ID（格式如 "student_xxx_0"）
            if not key.startswith('student_') and not key.startswith('exp_'):
                # 这是一个知识点的记忆数据
                if isinstance(value, dict):
                    # 保留有意义的记忆信息
                    self.student.long_term_memory[key] = {
                        "short_term_strength": value.get("short_term_strength", 0.0),
                        "long_term_strength": value.get("long_term_strength", 0.0),
                        "last_accessed": value.get("last_accessed"),
                        "access_count": value.get("access_count", 0),
                        "success_rate": value.get("success_rate", 0.0)
                    }
        
        logging.info(f"学生 {self.student.name} 同步了 {len(self.student.long_term_memory)} 个知识点到长期记忆")
    
    def load_memory_state(self, base_path: str):
        """加载记忆状态"""
        filepath = f"{base_path}/student_{self.student.id}_memory.json"
        
        # 检查文件是否存在
        if not os.path.exists(filepath):
            logging.info(f"学生 {self.student.name} 的记忆文件不存在，将从空白状态开始")
            return
            
        try:
            self.memory_system.load_memory_state(filepath)
            logging.info(f"成功加载学生 {self.student.name} 的记忆状态")
        except json.JSONDecodeError as e:
            logging.warning(f"学生 {self.student.name} 记忆文件格式错误: {e}，将重新开始")
            # 备份损坏的文件
            backup_path = f"{filepath}.backup"
            try:
                import shutil
                shutil.move(filepath, backup_path)
                logging.info(f"损坏的记忆文件已备份到: {backup_path}")
            except Exception:
                pass
        except Exception as e:
            logging.warning(f"加载学生 {self.student.name} 记忆状态失败: {e}")
            # 继续使用默认的空记忆状态
    
    def _update_legacy_memory(self, assignment: Assignment, work: StudentWork, course: Optional['Course']):
        """更新传统记忆系统（保持兼容性）"""
        if not course or not assignment.knowledge_points_covered:
            return
        
        # 保留原有的记忆更新逻辑以保持兼容性
        for kp_id in assignment.knowledge_points_covered:
            kp = course.get_knowledge_point_by_id(kp_id)
            if kp:
                # 更新短期记忆
                self.student.update_short_term_memory(
                    kp_id, 
                    {
                        "concepts": kp.key_concepts,
                        "last_practice": assignment.title,
                        "difficulty": assignment.difficulty_level,
                        "timestamp": work.submission_time.isoformat()
                    }
                )
                
                # 根据作业表现决定是否巩固到长期记忆
                estimated_performance = self._estimate_assignment_performance(work, assignment)
                if estimated_performance > 0.7:  # 表现良好，巩固记忆
                    mastery_improvement = 0.1 * estimated_performance
                    current_mastery = self.student.knowledge_mastery.get(kp_id, 0.0)
                    new_mastery = min(1.0, current_mastery + mastery_improvement)
                    
                    if new_mastery > 0.6:  # 达到基本掌握水平，转为长期记忆
                        self.student.consolidate_memory(kp_id, new_mastery)
        
        # 记录表现历史
        performance_record = {
            "assignment_id": assignment.id,
            "assignment_title": assignment.title,
            "knowledge_points": assignment.knowledge_points_covered,
            "estimated_score": self._estimate_assignment_performance(work, assignment) * 100,
            "difficulty_level": assignment.difficulty_level,
            "timestamp": work.submission_time.isoformat()
        }
        self.student.performance_history.append(performance_record)
        
        # 保持历史记录在合理范围内
        if len(self.student.performance_history) > 20:
            self.student.performance_history = self.student.performance_history[-20:]
    
    def _get_enhanced_system_prompt(self, assignment: Assignment = None) -> str:
        """获取增强的学生角色系统提示词"""
        basic_prompt = self._get_student_system_prompt(assignment)
        
        enhancement = """
你现在具备了智能记忆系统，可以：
1. 回顾和应用之前的学习经验
2. 识别相似的问题模式
3. 从成功和失败的案例中学习
4. 根据知识掌握情况调整学习策略

在完成作业时，请合理利用提供的经验案例和学习建议，展现出学习的连续性和成长性。
"""
        
        return basic_prompt + enhancement
        
        # 获取涉及知识点的记忆
        relevant_kp_ids = assignment.knowledge_points_covered
        memory_context = self.student.get_knowledge_context(relevant_kp_ids)
        
        # 添加相关的前置知识点
        for kp_id in relevant_kp_ids:
            kp = course.get_knowledge_point_by_id(kp_id)
            if kp and kp.prerequisites:
                prereq_context = self.student.get_knowledge_context(kp.prerequisites)
                # 合并前置知识点的记忆
                for key in ["short_term", "long_term", "mastery_levels"]:
                    memory_context[key].update(prereq_context[key])
        
        return memory_context
    
    def _build_memory_aware_prompt(self, assignment: Assignment, memory_context: Dict[str, Any]) -> str:
        """构建考虑记忆的作业提示词"""
        base_prompt = self._build_assignment_prompt(assignment)
        
        # 添加记忆相关的上下文
        memory_prompt = "\n\n=== 你的相关学习经验和记忆 ===\n"
        
        # 短期记忆（最近学习的内容）
        if memory_context.get("short_term"):
            memory_prompt += "最近学习的内容（可能记忆不够清晰）：\n"
            for kp_id, memory in memory_context["short_term"].items():
                if isinstance(memory, dict) and "concepts" in memory:
                    memory_prompt += f"- {kp_id}: {memory.get('concepts', '相关概念')}\n"
                elif isinstance(memory, str):
                    memory_prompt += f"- {kp_id}: {memory}\n"
        
        # 长期记忆（掌握较好的内容）
        if memory_context.get("long_term"):
            memory_prompt += "\n已经掌握的知识（可以熟练运用）：\n"
            for kp_id, memory in memory_context["long_term"].items():
                if isinstance(memory, dict) and "concepts" in memory:
                    memory_prompt += f"- {kp_id}: {memory.get('concepts', '已掌握概念')}\n"
                elif isinstance(memory, str):
                    memory_prompt += f"- {kp_id}: {memory}\n"
        
        # 掌握程度
        if memory_context.get("mastery_levels"):
            memory_prompt += "\n知识点掌握情况：\n"
            for kp_id, level in memory_context["mastery_levels"].items():
                mastery_desc = self._get_mastery_description(level)
                memory_prompt += f"- {kp_id}: {mastery_desc} (掌握度: {level:.1f}/1.0)\n"
        
        # 根据学生类型调整记忆应用策略
        memory_strategy = self._get_memory_strategy()
        memory_prompt += f"\n{memory_strategy}\n"
        
        return base_prompt + memory_prompt
    
    def _get_mastery_description(self, level: float) -> str:
        """获取掌握程度描述"""
        if level >= 0.8:
            return "熟练掌握"
        elif level >= 0.6:
            return "基本掌握"
        elif level >= 0.4:
            return "部分理解"
        else:
            return "初步了解"
    
    def _get_memory_strategy(self) -> str:
        """根据学生类型获取记忆应用策略"""
        if self.student.student_type.value == "excellent":
            return "请充分利用你已掌握的知识，在此基础上尝试创新和优化。对于不太确定的概念，可以尝试推理和类比。"
        elif self.student.student_type.value in ["below_average", "average"]:
            return "主要依赖你已经熟练掌握的知识点来完成作业。对于记忆模糊的内容，采用保守的实现方式，确保基本功能正确。"
        else:
            return "合理运用你的知识储备，对于掌握较好的部分可以发挥创意，对于不确定的部分要谨慎处理。"
    
    def _update_memory_after_assignment(self, assignment: Assignment, work: StudentWork, course: Optional['Course']):
        """作业完成后更新记忆系统"""
        if not course or not assignment.knowledge_points_covered:
            return
        
        # 模拟学习过程中的记忆更新
        for kp_id in assignment.knowledge_points_covered:
            kp = course.get_knowledge_point_by_id(kp_id)
            if kp:
                # 更新短期记忆
                self.student.update_short_term_memory(
                    kp_id, 
                    {
                        "concepts": kp.key_concepts,
                        "last_practice": assignment.title,
                        "difficulty": assignment.difficulty_level,
                        "timestamp": work.submission_time.isoformat()
                    }
                )
                
                # 根据作业表现决定是否巩固到长期记忆
                estimated_performance = self._estimate_assignment_performance(work, assignment)
                if estimated_performance > 0.7:  # 表现良好，巩固记忆
                    mastery_improvement = 0.1 * estimated_performance
                    current_mastery = self.student.knowledge_mastery.get(kp_id, 0.0)
                    new_mastery = min(1.0, current_mastery + mastery_improvement)
                    
                    if new_mastery > 0.6:  # 达到基本掌握水平，转为长期记忆
                        self.student.consolidate_memory(kp_id, new_mastery)
        
        # 记录表现历史
        performance_record = {
            "assignment_id": assignment.id,
            "assignment_title": assignment.title,
            "knowledge_points": assignment.knowledge_points_covered,
            "estimated_score": self._estimate_assignment_performance(work, assignment) * 100,
            "difficulty_level": assignment.difficulty_level,
            "timestamp": work.submission_time.isoformat()
        }
        self.student.performance_history.append(performance_record)
        
        # 保持历史记录在合理范围内
        if len(self.student.performance_history) > 20:
            self.student.performance_history = self.student.performance_history[-20:]
    
    def _estimate_assignment_performance(self, work: StudentWork, assignment: Assignment) -> float:
        """估算作业表现水平 - 改进版，考虑学习进步和记忆效果，提高整体分数分布"""
        # 提高基准表现，让优秀学生有机会得到高分
        base_performance = 0.75  # 从0.72提高到0.75
        
        # 根据学生类型调整 - 拉大差距，让优秀学生更容易得高分
        type_multipliers = {
            "excellent": 1.33,      # 优秀: 0.75 * 1.33 ≈ 1.0 (100分)
            "good": 1.20,           # 良好: 0.75 * 1.20 ≈ 0.9 (90分)
            "average": 1.07,        # 普通: 0.75 * 1.07 ≈ 0.8 (80分)
            "below_average": 0.93,  # 较差: 0.75 * 0.93 ≈ 0.7 (70分)
            "strict": 1.13,         # 严格: 0.75 * 1.13 ≈ 0.85 (85分)
            "lenient": 1.07,        # 宽松: 0.75 * 1.07 ≈ 0.8 (80分)
            "perfunctory": 0.80     # 敷衍: 0.75 * 0.80 ≈ 0.6 (60分)
        }
        
        performance = base_performance * type_multipliers.get(self.student.student_type.value, 1.0)
        
        # 考虑学习经验积累 - 渐进式改善
        assignments_completed = getattr(self.performance_metrics, 'assignments_completed', 0)
        learning_boost = min(0.12, assignments_completed * 0.025)  # 最多12%的提升
        performance += learning_boost
        
        # 根据记忆系统使用情况调整
        if hasattr(self.memory_system, 'case_library') and len(self.memory_system.case_library.cases) > 0:
            memory_boost = min(0.08, len(self.memory_system.case_library.cases) * 0.015)
            performance += memory_boost
        
        # 根据作业难度调整 - 更平滑的难度曲线，减少惩罚
        # 难度1: 1.15倍, 难度3: 1.0倍, 难度5: 0.85倍
        difficulty_factor = max(0.85, 1.25 - 0.08 * assignment.difficulty_level)
        performance *= difficulty_factor
        
        # 添加适度随机性
        performance *= random.uniform(0.92, 1.08)
        
        # 确保分数在合理范围内，允许优秀学生达到满分
        return min(1.0, max(0.4, performance))
    
    
    def _get_student_system_prompt(self, assignment: Assignment = None) -> str:
        """获取学生角色的系统提示词（支持多种课程类型）"""
        base_prompt = f"""你是一名{self.student.major}专业的{self.student.academic_level}学生，名字叫{self.student.name}。

学生特征：
- 学生类型：{self.student.student_type.value}
- GPA：{self.student.gpa}
- 编程经验：{self.student.programming_experience}年
- 性格特征：{self.student.personality_traits}

请根据你的学术水平和能力特点来完成作业。如果你是优秀学生，作业应该质量很高；如果你是基础较弱的学生，作业可能存在一些问题或不完善的地方。

作业完成后，请按以下格式输出：
=== 作业内容 ===
[这里是你的作业内容]

=== 文档说明 ===
[这里是你对作业的说明文档]

=== 预估工时 ===
[完成这个作业大概花费的小时数]

=== 自我评估 ===
"""
        
        # 动态添加评价维度
        if assignment:
            from config.course_config import get_course_config
            config = get_course_config()
            course_type = getattr(assignment, 'course_type', None) or config.infer_course_type(assignment.subject)
            dimensions = config.get_dimension_names(course_type)
            for dim in dimensions:
                base_prompt += f"{dim}: [0-100分]\n"
        else:
            # 默认使用编程类维度
            base_prompt += """功能实现: [0-100分]
代码质量: [0-100分] 
创新性: [0-100分]
文档完整性: [0-100分]
"""
        
        return base_prompt
    
    def _build_assignment_prompt(self, assignment: Assignment) -> str:
        """构建作业提示词"""
        prompt = f"""请完成以下作业：

作业标题：{assignment.title}
作业描述：{assignment.description}
作业类型：{assignment.assignment_type.value}
所属课程：{assignment.subject}
难度等级：{assignment.difficulty_level}/5

具体要求：
"""
        for i, req in enumerate(assignment.requirements, 1):
            prompt += f"{i}. {req}\n"
        
        prompt += f"\n评价标准：\n"
        for criterion, description in assignment.evaluation_criteria.items():
            prompt += f"- {criterion}: {description}\n"
        
        return prompt
    
    def _create_student_work(self, assignment: Assignment, content: str) -> StudentWork:
        """从LLM响应创建学生作品对象"""
        import uuid
        from datetime import datetime
        
        # 解析响应内容
        sections = self._parse_response(content)
        
        # 生成自我评估（传递assignment参数）
        self_assessment = self._generate_self_assessment(sections.get("自我评估", ""), assignment)
        
        return StudentWork(
            id=str(uuid.uuid4()),
            student_id=self.student.id,
            assignment_id=assignment.id,
            content=sections.get("作业内容", content),
            documentation=sections.get("文档说明", ""),
            submission_time=datetime.now(),
            estimated_effort_hours=self._parse_effort_hours(sections.get("预估工时", "5")),
            self_assessment=self_assessment
        )
    
    def _parse_response(self, content: str) -> Dict[str, str]:
        """解析LLM响应的结构化内容 - 改进版本，正确处理代码块"""
        sections = {}
        current_section = None
        current_content = []
        in_code_block = False
        
        lines = content.split('\n')
        for line in lines:
            # 检测代码块开始/结束
            stripped = line.strip()
            if stripped.startswith('```'):
                in_code_block = not in_code_block
                if current_section:
                    current_content.append(line)
                continue
            
            # 只有在代码块外才检测段落标题
            if not in_code_block and line.startswith('=== ') and line.endswith(' ==='):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[4:-4]
                current_content = []
            else:
                if current_section:
                    current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # 如果"作业内容"段落太短，尝试提取代码块
        if "作业内容" in sections and len(sections["作业内容"]) < 50:
            import re
            code_match = re.search(r'```(?:python|cpp|java)?[\s\S]*?```', content)
            if code_match:
                sections["作业内容"] = code_match.group(0)
                logging.info(f"从代码块提取作业内容: {len(sections['作业内容'])}字符")
        
        return sections
    
    def _parse_effort_hours(self, effort_text: str) -> int:
        """解析工时信息"""
        try:
            # 尝试从文本中提取数字
            import re
            numbers = re.findall(r'\d+', effort_text)
            if numbers:
                return int(numbers[0])
        except:
            pass
        
        # 默认根据学生类型返回不同的工时
        if self.student.student_type.value == "excellent":
            return 8
        elif self.student.student_type.value == "good":
            return 6
        elif self.student.student_type.value == "average":
            return 5
        elif self.student.student_type.value == "perfunctory":
            return 3  # 敷衍学生工作时间较短
        else:
            return 4
    
    def _generate_self_assessment(self, assessment_text: str, assignment: Assignment = None) -> Dict[str, int]:
        """生成自我评估分数（支持多种课程类型）"""
        import re
        
        # 动态获取评价维度
        if assignment:
            from config.course_config import get_course_config
            config = get_course_config()
            course_type = getattr(assignment, 'course_type', None) or config.infer_course_type(assignment.subject)
            dimensions = config.get_dimension_names(course_type)
        else:
            # 如果没有assignment信息，使用默认编程类维度
            dimensions = ["功能实现", "代码质量", "创新性", "文档完整性"]
        
        # 尝试从文本中解析分数
        scores = {}
        for dim in dimensions:
            pattern = f"{dim}[：:]\\s*(\\d+)"
            match = re.search(pattern, assessment_text)
            if match:
                scores[dim] = int(match.group(1))
            else:
                # 根据学生类型生成默认分数
                scores[dim] = self._get_default_self_score(dim)
        
        return scores
    
    def _convert_new_to_old_retrieval(self, new_result, memory_context):
        """将新记忆系统的检索结果转换为旧格式"""
        from memory import MemoryRetrievalResult
        
        # 将新记忆转换为旧的case格式
        retrieved_cases = []
        similarity_scores = []
        
        for i, memory in enumerate(new_result.retrieved_memories):
            # 构建case对象
            case = {
                'id': memory.id,
                'problem_description': memory.content,
                'solution': '',
                'success_score': memory.success_score,
                'timestamp': memory.timestamp.isoformat() if hasattr(memory.timestamp, 'isoformat') else str(memory.timestamp),
                'knowledge_points': getattr(memory, 'knowledge_points', []),
            }
            
            # 根据记忆类型添加不同的信息
            if hasattr(memory, 'score'):
                case['solution'] = f"得分: {memory.score:.1f}分"
                if hasattr(memory, 'reflection'):
                    case['solution'] += f"\n反思: {memory.reflection[:100]}..."
            elif hasattr(memory, 'evaluation_content'):
                case['solution'] = f"评价经验: {memory.evaluation_content[:100]}..."
            elif hasattr(memory, 'received_evaluation'):
                case['solution'] = f"收到反馈: {memory.received_evaluation[:100]}..."
            
            retrieved_cases.append(case)
            
            # 获取相似度分数（从priority_scores中获取）
            if i < len(new_result.priority_scores):
                similarity_scores.append(new_result.priority_scores[i].retrieval_probability)
            else:
                similarity_scores.append(0.5)
        
        # 计算置信度
        if similarity_scores:
            confidence_level = sum(similarity_scores) / len(similarity_scores)
        else:
            confidence_level = 0.0
        
        # 生成解释文本
        if retrieved_cases:
            explanation = f"从新记忆系统检索到 {len(retrieved_cases)} 条相关记忆，"
            explanation += f"包含 {new_result.dimensions_retrieved} 个维度的经验。"
        else:
            explanation = "未找到相关的历史记忆。"
        
        # 创建旧格式的检索结果
        return MemoryRetrievalResult(
            retrieved_cases=retrieved_cases,
            similarity_scores=similarity_scores,
            retrieval_time_ms=0.0,  # 添加缺失字段
            confidence_level=confidence_level,
            explanation=explanation
        )
    
    def _get_default_self_score(self, dimension: str) -> int:
        """根据学生类型获取默认自评分数"""
        import random
        
        base_scores = {
            "excellent": random.randint(85, 95),
            "good": random.randint(75, 85),
            "average": random.randint(65, 75),
            "below_average": random.randint(55, 70),
            "strict": random.randint(60, 75),  # 严格的学生自评较低
            "lenient": random.randint(80, 90),  # 宽松的学生自评较高
            "perfunctory": random.randint(70, 80)  # 敷衍学生自评随意，偏中上
        }
        
        return base_scores.get(self.student.student_type.value, 70)
    
    # ==================== 新记忆系统相关方法 ====================
    
    def _store_to_new_memory_system(
        self,
        assignment: Assignment,
        work: StudentWork,
        learning_outcome: LearningOutcome,
        retrieval_result
    ):
        """存储到新记忆系统（三维记忆）"""
        try:
            # 创建学习记忆
            learning_memory = LearningMemory(
                id=f"mem_learn_{assignment.id}_{self.student.id}_{uuid.uuid4().hex[:8]}",
                content=f"完成了{assignment.title}作业，涉及{', '.join(assignment.knowledge_points_covered[:3])}等知识点",
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                knowledge_points=assignment.knowledge_points_covered,
                score=learning_outcome.score,
                time_spent=learning_outcome.time_spent,
                difficulties_encountered=learning_outcome.errors_made if learning_outcome.errors_made else [],
                breakthroughs=learning_outcome.concepts_learned[:2] if learning_outcome.concepts_learned else [],
                learning_strategies=["记忆检索", "经验回放"] if retrieval_result.retrieved_cases else ["独立思考"],
                reflection=learning_outcome.reflection,
                importance=self._calculate_memory_importance(assignment, learning_outcome),
                success_score=learning_outcome.score / 100,
                is_breakthrough=(learning_outcome.score >= 90 and len(learning_outcome.concepts_learned) > 3)
            )
            
            self.new_memory_system.add_memory(learning_memory)
            logging.info(f"学习记忆已添加: {learning_memory.id}")
            
        except Exception as e:
            logging.error(f"存储到新记忆系统失败: {e}")
    
    def _calculate_memory_importance(self, assignment: Assignment, learning_outcome: LearningOutcome) -> float:
        """
        计算学习记忆重要性（分段累加）
        
        范围: 0.5 ~ 1.0
        - 基础值: 0.5
        - 分数加成: +0.1~0.3
        - 新概念加成: +0.2
        - 难度加成: +0.1
        - 突破事件加成: +0.15
        """
        importance = 0.5  # 基础重要性
        
        # 分数高增加重要性
        if learning_outcome.score >= 90:
            importance += 0.3
        elif learning_outcome.score >= 80:
            importance += 0.2
        elif learning_outcome.score >= 70:
            importance += 0.1
        
        # 学到新概念增加重要性
        if learning_outcome.concepts_learned and len(learning_outcome.concepts_learned) > 2:
            importance += 0.2
        
        # 难度高的作业重要性高
        if hasattr(assignment, 'difficulty_level') and assignment.difficulty_level > 0.7:
            importance += 0.1
        
        # 突破事件增加重要性（新增）
        if hasattr(learning_outcome, 'is_breakthrough') and learning_outcome.is_breakthrough:
            importance += 0.15
        
        return min(1.0, importance)
    
    def evaluate_peer_work(self, peer_work: StudentWork, assignment: Assignment) -> Dict[str, Any]:
        """评价同伴作业（支持多种课程类型）"""
        logging.info(f"学生 {self.student.name} 开始评价 {peer_work.student_id} 的作业")
        
        # 动态获取评价维度
        from config.course_config import get_course_config
        config = get_course_config()
        
        # 获取课程类型（优先使用assignment的course_type，否则推断）
        course_type = getattr(assignment, 'course_type', None) or config.infer_course_type(assignment.subject)
        dimensions = config.get_dimension_names(course_type)
        descriptions = config.get_dimension_descriptions(course_type)
        
        # 【新增】检索过往评价经验
        evaluation_context = ""
        if self.use_new_memory:
            try:
                query = f"评价{assignment.title}作业，涉及{', '.join(assignment.knowledge_points_covered[:2]) if assignment.knowledge_points_covered else '基础知识'}"
                retrieval_result = self.new_memory_system.retrieve(
                    query=query,
                    dimension_filter=[
                        MemoryDimension.PEER_EVALUATION,  # 我过往的评价经验
                        MemoryDimension.RECEIVED_EVALUATION  # 我收到过的评价
                    ],
                    top_k=3
                )
                
                if retrieval_result.retrieved_memories:  # 修复：使用正确的属性名
                    eval_examples = []
                    for mem in retrieval_result.retrieved_memories[:2]:
                        if hasattr(mem, 'evaluation_content'):
                            eval_examples.append(f"- {mem.evaluation_content[:100]}...")
                        elif hasattr(mem, 'received_evaluation'):
                            eval_examples.append(f"- 参考案例: {mem.received_evaluation[:100]}...")
                    
                    if eval_examples:
                        evaluation_context = "\n\n【参考过往评价经验】\n" + "\n".join(eval_examples)
                        logging.info(f"检索到{len(eval_examples)}条评价经验用于参考")
            except Exception as e:
                logging.warning(f"检索评价经验失败: {e}")
                evaluation_context = ""
        
        # 构建评价提示词
        prompt = f"""你是一名{self.student.student_type.value}类型的学生，现在需要评价同伴的作业。

作业题目：{assignment.title}
作业描述：{assignment.description}
课程类型：{config.get_course_type_name(course_type)}
涉及知识点：{', '.join(assignment.knowledge_points_covered) if assignment.knowledge_points_covered else '无'}

同伴的作业内容：
{peer_work.content[:1000]}...
{evaluation_context}

请从以下几个方面评价：
"""
        for i, dim in enumerate(dimensions, 1):
            prompt += f"{i}. {dim}（{descriptions[dim]}）\n"
        
        prompt += """
请给出具体评价和建议，并打分（0-100分）。
返回格式：
评价内容：
[你的评价]

优点：
- [优点1]
- [优点2]

不足：
- [不足1]
- [不足2]

建议：
- [建议1]

总分：[分数]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": self._get_evaluation_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            evaluation_content = response.choices[0].message.content
            
            # 解析评价
            evaluation_data = self._parse_evaluation(evaluation_content)
            
            # 存储评价记忆
            if self.use_new_memory:
                self._store_peer_evaluation_memory(
                    peer_work, assignment, evaluation_data
                )
            
            # 【新增】更新互评次数
            self.performance_metrics['total_evaluations'] += 1
            
            # 【新增】评价他人后，使用评价质量作为反馈
            # 评价质量基于评价的详细程度
            eval_quality = 0.6  # 基础质量
            if evaluation_data.get('strengths') and len(evaluation_data['strengths']) > 1:
                eval_quality += 0.1
            if evaluation_data.get('weaknesses') and len(evaluation_data['weaknesses']) > 1:
                eval_quality += 0.1
            if evaluation_data.get('suggestions') and len(evaluation_data['suggestions']) > 0:
                eval_quality += 0.2
            
            # 注意：这里不更新assignment_score，因为这不是自己的作业
            # 只记录评价活动提升了元认知能力
            
            return evaluation_data
            
        except Exception as e:
            logging.error(f"评价生成失败: {e}")
            return {
                "content": "评价生成失败",
                "score": 70,
                "strengths": [],
                "weaknesses": [],
                "suggestions": []
            }
    
    def _get_evaluation_system_prompt(self) -> str:
        """获取评价系统提示词"""
        personality_traits = {
            "excellent": "你是一名优秀的学生，评价标准严格，注重细节和深度。",
            "good": "你是一名优良的学生，评价客观公正，有一定深度。",
            "average": "你是一名普通学生，评价较为表面，关注基本要求。",
            "strict": "你是一名严格的评价者，标准很高，不轻易给高分。",
            "lenient": "你是一名宽松的评价者，倾向于给高分和鼓励。",
            "perfunctory": "你的评价较为简单，不太深入。"
        }
        
        return personality_traits.get(
            self.student.student_type.value,
            "你是一名学生，正在认真评价同伴的作业。"
        )
    
    def _parse_evaluation(self, evaluation_text: str) -> Dict[str, Any]:
        """解析评价内容"""
        import re
        
        # 提取总分
        score_match = re.search(r'总分[：:]\s*(\d+)', evaluation_text)
        score = int(score_match.group(1)) if score_match else 75
        
        # 提取优点
        strengths = []
        strengths_section = re.search(r'优点[：:](.*?)(?:不足|建议|总分|$)', evaluation_text, re.DOTALL)
        if strengths_section:
            strengths = [s.strip('- ').strip() for s in strengths_section.group(1).split('\n') if s.strip() and s.strip().startswith('-')]
        
        # 提取不足
        weaknesses = []
        weaknesses_section = re.search(r'不足[：:](.*?)(?:建议|总分|$)', evaluation_text, re.DOTALL)
        if weaknesses_section:
            weaknesses = [w.strip('- ').strip() for w in weaknesses_section.group(1).split('\n') if w.strip() and w.strip().startswith('-')]
        
        # 提取建议
        suggestions = []
        suggestions_section = re.search(r'建议[：:](.*?)(?:总分|$)', evaluation_text, re.DOTALL)
        if suggestions_section:
            suggestions = [s.strip('- ').strip() for s in suggestions_section.group(1).split('\n') if s.strip() and s.strip().startswith('-')]
        
        return {
            "content": evaluation_text,
            "score": score,
            "strengths": strengths[:3],  # 限制数量
            "weaknesses": weaknesses[:3],
            "suggestions": suggestions[:3]
        }
    
    def _store_peer_evaluation_memory(
        self,
        peer_work: StudentWork,
        assignment: Assignment,
        evaluation_data: Dict[str, Any]
    ):
        """存储评价他人的记忆"""
        try:
            # 从评价中学到的
            learning_points = []
            if evaluation_data["strengths"]:
                learning_points.extend([f"学到了{s}" for s in evaluation_data["strengths"][:2]])
            
            # 计算importance（基于评价质量）
            importance = 0.5  # 基础重要性
            
            # 评价丰富度
            strength_count = len(evaluation_data.get("strengths", []))
            weakness_count = len(evaluation_data.get("weaknesses", []))
            
            if strength_count >= 2:
                importance += 0.1
            if weakness_count >= 2:
                importance += 0.1
            if evaluation_data.get("suggestions") and len(evaluation_data["suggestions"]) >= 1:
                importance += 0.15
            
            # 学习收获
            if len(learning_points) > 0:
                importance += 0.15
            
            importance = min(1.0, importance)
            
            peer_eval_memory = PeerEvaluationMemory(
                id=f"mem_eval_{peer_work.id}_{self.student.id}_{uuid.uuid4().hex[:8]}",
                content=f"评价了{peer_work.student_id}在{assignment.title}作业中的表现",
                evaluated_student_id=peer_work.student_id,
                evaluated_work_id=peer_work.id,
                assignment_id=assignment.id,
                evaluation_content=evaluation_data["content"][:500],  # 限制长度
                evaluation_score=evaluation_data["score"],
                observed_strengths=evaluation_data["strengths"],
                observed_weaknesses=evaluation_data["weaknesses"],
                learning_from_peer=learning_points,
                self_reflection=f"通过评价他人，反思自己在{', '.join(assignment.knowledge_points_covered[:2])}方面的掌握程度",
                importance=importance
            )
            
            self.new_memory_system.add_memory(peer_eval_memory)
            logging.info(f"评价记忆已添加: {peer_eval_memory.id}, importance={importance:.2f}")
            
        except Exception as e:
            logging.error(f"存储评价记忆失败: {e}")
    
    def receive_peer_evaluation(
        self,
        evaluation_data: Dict[str, Any],
        evaluator_id: str,
        my_work: StudentWork,
        assignment: Assignment
    ):
        """接收同伴评价"""
        logging.info(f"学生 {self.student.name} 收到来自 {evaluator_id} 的评价")
        
        try:
            # 分析评价的认同程度
            agreement = self._assess_agreement_level(evaluation_data, my_work)
            
            # 提取洞察
            insights = self._extract_insights(evaluation_data)
            
            # 计划改进行动
            improvements = self._plan_improvements(evaluation_data, assignment)
            
            # 更新心理状态（基于收到的评价）- 已禁用
            # self._update_psychology_after_feedback(evaluation_data, evaluator_id, agreement)
            # self._save_psychology_state()
            
            # 存储被评价记忆
            if self.use_new_memory:
                # 计算importance（基于建设性和认同度）
                importance = 0.6  # 基础值（收到评价本身就重要）
                
                # 建设性（已有数据）
                insight_count = len(insights)
                improvement_count = len(improvements)
                
                if insight_count >= 2:
                    importance += 0.1
                if improvement_count >= 2:
                    importance += 0.15
                
                # 认同度（已有数据）
                if agreement >= 0.7:
                    importance += 0.1
                elif agreement <= 0.3:
                    importance -= 0.05  # 低认同度降权
                
                importance = min(1.0, max(0.3, importance))  # 限制范围 [0.3, 1.0]
                
                received_memory = ReceivedEvaluationMemory(
                    id=f"mem_received_{my_work.id}_{evaluator_id}_{uuid.uuid4().hex[:8]}",
                    content=f"收到了{evaluator_id}对我{assignment.title}作业的评价",
                    evaluator_student_id=evaluator_id,
                    own_work_id=my_work.id,
                    assignment_id=assignment.id,
                    received_evaluation=evaluation_data["content"][:500],
                    received_score=evaluation_data["score"],
                    agreement_level=agreement,
                    insights_gained=insights,
                    improvement_actions=improvements,
                    reflection_on_feedback=self._reflect_on_feedback(evaluation_data, agreement),
                    importance=importance
                )
                
                self.new_memory_system.add_memory(received_memory)
                logging.info(f"被评价记忆已添加: {received_memory.id}, importance={importance:.2f}, agreement={agreement:.2f}")
                
        except Exception as e:
            logging.error(f"处理收到的评价失败: {e}")
    
    def _assess_agreement_level(self, evaluation_data: Dict[str, Any], my_work: StudentWork) -> float:
        """评估对评价的认同程度"""
        # 简化实现：基于分数差异和学生类型
        score_diff = abs(evaluation_data["score"] - getattr(my_work, 'self_score', 75))
        
        if score_diff < 5:
            base_agreement = 0.9
        elif score_diff < 10:
            base_agreement = 0.7
        elif score_diff < 20:
            base_agreement = 0.5
        else:
            base_agreement = 0.3
        
        # 学生类型影响认同度
        if self.student.student_type.value == "strict":
            base_agreement -= 0.1  # 严格的学生更挑剔
        elif self.student.student_type.value == "lenient":
            base_agreement += 0.1  # 宽松的学生更接受
        
        return max(0.0, min(1.0, base_agreement))
    
    def _extract_insights(self, evaluation_data: Dict[str, Any]) -> List[str]:
        """从评价中提取洞察"""
        insights = []
        
        if evaluation_data.get("weaknesses"):
            for weakness in evaluation_data["weaknesses"][:2]:
                insights.append(f"意识到：{weakness}")
        
        if evaluation_data.get("suggestions"):
            for suggestion in evaluation_data["suggestions"][:2]:
                insights.append(f"建议：{suggestion}")
        
        return insights
    
    def _plan_improvements(self, evaluation_data: Dict[str, Any], assignment: Assignment) -> List[str]:
        """计划改进行动"""
        improvements = []
        
        if evaluation_data.get("weaknesses"):
            for weakness in evaluation_data["weaknesses"][:2]:
                improvements.append(f"改进{weakness}")
        
        if evaluation_data.get("suggestions"):
            improvements.append(f"在下次作业中应用建议")
        
        # 基于知识点的改进
        if assignment.knowledge_points_covered:
            weak_kp = assignment.knowledge_points_covered[0]
            improvements.append(f"加强{weak_kp}的学习")
        
        return improvements[:3]  # 限制数量
    
    def _reflect_on_feedback(self, evaluation_data: Dict[str, Any], agreement: float) -> str:
        """对反馈进行反思"""
        if agreement > 0.7:
            return f"这个评价很有帮助，我认同其中的{int(agreement*100)}%。会认真考虑改进建议。"
        elif agreement > 0.4:
            return f"评价有一定参考价值，我部分认同。会选择性地采纳建议。"
        else:
            return f"评价的观点与我的理解有较大差异，需要进一步思考和验证。"
    
    def advance_round(self):
        """推进到下一轮（触发记忆巩固）"""
        if self.use_new_memory:
            self.new_memory_system.advance_round()
            
            # 更新知识掌握度到记忆系统
            for kp, mastery in self.student.knowledge_mastery.items():
                self.new_memory_system.update_knowledge_mastery(kp, mastery)
            
            logging.info(f"学生 {self.student.name} 推进到下一轮，触发记忆巩固")
    
    def revise_work(
        self,
        original_work: StudentWork,
        assignment: Assignment,
        received_evaluations: List[Dict[str, Any]],
        round_number: int
    ) -> StudentWork:
        """
        根据收到的同伴评价修改作业
        
        Args:
            original_work: 原始作业
            assignment: 作业对象
            received_evaluations: 收到的评价列表
            round_number: 当前轮次
        
        Returns:
            修改后的新作业对象
        """
        logging.info(f"学生 {self.student.name} 开始修改作业（第{round_number}轮后）")
        
        try:
            # 1. 整理收到的反馈
            feedback_summary = self._summarize_feedback(received_evaluations)
            
            # 2. 从记忆系统检索相关改进经验
            improvement_context = self._retrieve_improvement_experience(assignment, feedback_summary)
            
            # 3. 使用LLM生成修改后的作业
            revised_content = self._generate_revised_work(
                original_work=original_work,
                assignment=assignment,
                feedback_summary=feedback_summary,
                improvement_context=improvement_context,
                round_number=round_number
            )
            
            # 4. 在原始作业上添加修订历史（保留原作业，只添加历史记录）
            # 初始化revision_history
            if not hasattr(original_work, 'revision_history') or original_work.revision_history is None:
                original_work.revision_history = []
            
            # 计算修改后的分数（个性化评分）
            revised_score = self._calculate_personalized_score(
                original_score=feedback_summary.get('average_score', 75),
                improvement_score=revised_content.get('improvement_score', 0.5),
                feedback_avg=feedback_summary.get('average_score', 75)
            )
            
            # 创建修订记录
            revision_record = {
                "round_number": round_number,
                "revision_time": datetime.now().isoformat(),
                "revised_content": revised_content["content"],
                "documentation": revised_content.get("documentation", ""),
                "reflection": revised_content.get("reflection", ""),
                "improvement_score": revised_content.get("improvement_score", 0.5),
                "revised_score": revised_score,
                "feedback_summary": {
                    "average_score": feedback_summary.get("average_score", 75),
                    "areas_to_improve": feedback_summary.get("areas_to_improve", [])[:3],
                    "evaluation_count": len(received_evaluations)
                }
            }
            
            # 添加到历史记录
            original_work.revision_history.append(revision_record)
            
            # 更新作业的当前内容为修改后的内容
            original_work.content = revised_content["content"]
            original_work.documentation = revised_content.get("documentation", original_work.documentation)
            original_work.revision_number = getattr(original_work, 'revision_number', 0) + 1
            original_work.revision_notes = f"第{round_number}轮修改：{revised_content.get('documentation', '')[:50]}..."
            
            # 5. 存储修改记忆（包含深度反思和改进评估）
            if self.use_new_memory:
                self._store_revision_memory(
                    original_work=original_work,
                    revised_work=original_work,  # 传递同一个对象
                    feedback_summary=feedback_summary,
                    round_number=round_number,
                    assignment=assignment,
                    revision_data=revised_content  # 传递包含reflection和improvement_score的数据
                )
            
            logging.info(f"学生 {self.student.name} 完成第{round_number}轮作业修改，添加到revision_history")
            return original_work
            
        except Exception as e:
            logging.error(f"作业修改失败: {e}")
            return original_work
    
    def _summarize_feedback(self, evaluations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """整理并总结收到的反馈"""
        if not evaluations:
            return {
                "summary": "没有收到反馈", 
                "key_points": [], 
                "scores": [], 
                "average_score": 75,
                "strengths": [],
                "areas_to_improve": []
            }
        
        scores = []
        strengths = []
        weaknesses = []
        suggestions = []
        
        for eval_data in evaluations:
            # 处理scores - 可能是字典对象或单个值
            if "scores" in eval_data:
                score_obj = eval_data["scores"]
                if isinstance(score_obj, dict):
                    # 计算加权总分
                    if "dimension_scores" in score_obj and score_obj["dimension_scores"]:
                        # 使用通用维度分数
                        dim_scores = score_obj["dimension_scores"]
                        avg = sum(dim_scores.values()) / len(dim_scores) if dim_scores else 75
                        scores.append(avg)
                    else:
                        # 使用固定维度（编程类）
                        scores.append(
                            score_obj.get("functionality", 0) * 0.4 +
                            score_obj.get("code_quality", 0) * 0.3 +
                            score_obj.get("innovation", 0) * 0.15 +
                            score_obj.get("documentation", 0) * 0.15
                        )
                else:
                    scores.append(float(score_obj))
            elif "score" in eval_data:
                scores.append(eval_data["score"])
            
            # 处理comments - 新的数据结构
            if "comments" in eval_data and isinstance(eval_data["comments"], dict):
                comments = eval_data["comments"]
                if "strengths" in comments and comments["strengths"]:
                    strengths.append(comments["strengths"])
                if "weaknesses" in comments and comments["weaknesses"]:
                    weaknesses.append(comments["weaknesses"])
                if "suggestions" in comments and comments["suggestions"]:
                    suggestions.append(comments["suggestions"])
            
            # 处理overall_comment
            if "overall_comment" in eval_data and eval_data["overall_comment"]:
                content = eval_data["overall_comment"]
                if "优点" in content or "strengths" in content.lower():
                    strengths.append(content)
                if "不足" in content or "weakness" in content.lower():
                    weaknesses.append(content)
            
            # 兼容旧格式 - content字段
            if "content" in eval_data:
                content = eval_data["content"]
                if "优点" in content or "strengths" in content.lower():
                    strengths.append(content)
                if "不足" in content or "weakness" in content.lower():
                    weaknesses.append(content)
                if "建议" in content or "suggestion" in content.lower():
                    suggestions.append(content)
        
        avg_score = sum(scores) / len(scores) if scores else 75
        
        # 提取关键改进点（从weaknesses和suggestions中提取）
        areas_to_improve = []
        for w in weaknesses[:3]:
            # 提取前100字作为改进点
            areas_to_improve.append(w[:100] if len(w) > 100 else w)
        
        return {
            "summary": f"收到{len(evaluations)}份评价，平均分{avg_score:.1f}分",
            "average_score": avg_score,
            "key_points": suggestions[:3] if suggestions else areas_to_improve[:2],
            "strengths": strengths[:2],
            "areas_to_improve": areas_to_improve if areas_to_improve else ["需要进一步改进"]
        }
    
    def _retrieve_improvement_experience(self, assignment: Assignment, feedback_summary: Dict[str, Any]) -> str:
        """检索改进相关的经验"""
        if not self.use_new_memory:
            return ""
        
        try:
            query = f"如何改进作业：{assignment.title}。需要提升：{', '.join(feedback_summary.get('areas_to_improve', [])[:2])}"
            result = self.new_memory_system.retrieve(
                query=query,
                top_k=3,
                dimension_filter=[
                    MemoryDimension.LEARNING,
                    MemoryDimension.RECEIVED_EVALUATION
                ]
            )
            
            context_parts = []
            for memory in result.retrieved_memories[:3]:
                if hasattr(memory, 'reflection'):
                    context_parts.append(f"- 过往经验: {memory.reflection}")
                elif hasattr(memory, 'insights_gained'):
                    context_parts.append(f"- 改进洞察: {', '.join(memory.insights_gained[:2])}")
            
            return "\n".join(context_parts) if context_parts else "首次修改，无历史经验"
        except Exception as e:
            logging.warning(f"检索改进经验失败: {e}")
            return "首次修改，无历史经验"
    
    def _generate_revised_work(self, original_work: StudentWork, assignment: Assignment,
                               feedback_summary: Dict[str, Any], improvement_context: str,
                               round_number: int) -> Dict[str, Any]:
        """使用LLM生成修改后的作业"""
        from config.course_config import get_course_config
        config = get_course_config()
        course_type = getattr(assignment, 'course_type', None) or config.infer_course_type(assignment.subject)
        
        # 检索过往的学习记忆和收到的评价，生成个性化的反思提示
        personal_context = self._build_personal_reflection_context(assignment)
        
        prompt = f"""你是一名{self.student.student_type.value}类型的学生，正在根据同伴反馈修改你的作业。

【原作业】
{original_work.content[:800]}

【收到的反馈摘要】
{feedback_summary['summary']}
平均分：{feedback_summary.get('average_score', 75):.1f}

需要改进的方面：
{chr(10).join('- ' + str(item) for item in feedback_summary.get('areas_to_improve', ['无'])[:3])}

【你的学习背景和过往经验】
{personal_context}

【过往改进经验】
{improvement_context}

【作业要求】
{assignment.description}

请根据反馈改进你的作业。注意：
1. 保留原作业的优点
2. 针对性地改进被指出的不足
3. 体现你对反馈的理解和思考
4. 改进应该是实质性的，不是简单重写
5. **必须结合你的个人学习背景和经验进行反思**

返回格式：
改进后的内容：
[你的改进版本]

改进说明：
[详细说明你做了哪些具体改进，至少100字，包括：
1. 我具体改了什么地方（引用代码行或功能模块）
2. 为什么这样改（基于哪条具体的反馈）
3. 改进后的预期效果是什么]

深度反思：
[结合你的个人学习特点和过往经验，至少80字，必须回答：
1. 这次改进让我意识到了什么问题？
2. 这个问题和我之前的学习习惯有什么关系？
3. 我打算如何避免类似问题？
4. 这次经历对我的学习方法有什么启发？]

自我评估：
[评估改进程度，0-100分]
"""
        
        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": self._get_student_system_prompt(assignment)},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            sections = self._parse_revision_response(content)
            
            # 验证反思质量
            improvement_desc = sections.get("改进说明", "")
            reflection = sections.get("深度反思", "")
            
            # 强制最低字数要求
            if len(improvement_desc) < 50:
                improvement_desc = f"根据反馈改进了以下方面：{', '.join(feedback_summary.get('areas_to_improve', ['多个方面'])[:3])}。{improvement_desc}"
            
            if len(reflection) < 50:
                reflection = self._generate_fallback_reflection(feedback_summary, improvement_context)
            
            # 计算改进评估分数（用于个性化评分）
            improvement_score = self._calculate_improvement_score(
                original_work, sections, feedback_summary
            )
            
            # 获取改进后的内容，确保不为空
            revised_content = sections.get("改进后的内容", "")
            if not revised_content or len(revised_content) < 50:
                # 如果解析出的内容太短，尝试从原始响应中提取代码
                logging.warning(f"改进后的内容太短({len(revised_content)}字符)，尝试从原始响应提取")
                # 尝试提取代码块
                import re
                code_match = re.search(r'```(?:python|cpp|java)?\n([\s\S]*?)```', content)
                if code_match:
                    revised_content = code_match.group(0)  # 包含代码块标记
                    logging.info(f"从代码块提取到内容: {len(revised_content)}字符")
                else:
                    # 如果没有代码块，使用原始内容
                    revised_content = original_work.content
                    logging.warning("未找到代码块，保留原始内容")
            
            return {
                "content": revised_content,
                "documentation": improvement_desc,
                "reflection": reflection,
                "improvement_score": improvement_score,
                "self_assessment": None
            }
        except Exception as e:
            logging.error(f"生成修改版本失败: {e}")
            fallback_reflection = self._generate_fallback_reflection(feedback_summary, improvement_context)
            return {
                "content": original_work.content,
                "documentation": f"尝试根据反馈改进了{', '.join(feedback_summary.get('areas_to_improve', ['相关问题'])[:2])}",
                "reflection": fallback_reflection,
                "improvement_score": 0.5,
                "self_assessment": None
            }
    
    def _parse_revision_response(self, content: str) -> Dict[str, str]:
        """解析修改响应 - 改进版本，正确处理代码块"""
        sections = {}
        current_section = None
        current_content = []
        in_code_block = False
        
        # 定义已知的段落标题
        known_sections = ['改进后的内容', '改进说明', '深度反思', '自我评估']
        
        for line in content.split('\n'):
            stripped_line = line.strip()
            
            # 检测代码块开始/结束
            if stripped_line.startswith('```'):
                in_code_block = not in_code_block
                if current_section:
                    current_content.append(line)  # 保留原始行（包含空格）
                continue
            
            # 只有在代码块外才检测新段落
            if not in_code_block:
                # 检查是否是段落标题
                section_title = stripped_line.rstrip('：:')
                if section_title in known_sections:
                    if current_section and current_content:
                        sections[current_section] = '\n'.join(current_content).strip()
                    current_section = section_title
                    current_content = []
                    continue
            
            # 添加内容到当前段落
            if current_section:
                current_content.append(line)  # 保留原始行（包含空格和缩进）
        
        if current_section and current_content:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # 调试：检查解析结果
        for key, value in sections.items():
            if len(value) < 20:
                logging.warning(f"段落 '{key}' 内容过短: {len(value)}字符")
        
        return sections
    
    def _build_personal_reflection_context(self, assignment: Assignment) -> str:
        """构建个性化的反思上下文（从记忆中检索学生的学习特点）"""
        if not self.use_new_memory:
            return f"你是{self.student.student_type.value}类型的学生，GPA {self.student.gpa:.2f}"
        
        try:
            # 检索与该作业相关的学习记忆
            query = f"我在{assignment.title}相关作业中的学习表现和困难"
            result = self.new_memory_system.retrieve(
                query=query,
                top_k=3,
                dimension_filter=[MemoryDimension.LEARNING, MemoryDimension.RECEIVED_EVALUATION]
            )
            
            context_parts = [
                f"你是{self.student.student_type.value}类型的学生，GPA {self.student.gpa:.2f}，编程经验{self.student.programming_experience}年"
            ]
            
            # 添加过往的困难和反思
            for memory in result.retrieved_memories[:2]:
                if hasattr(memory, 'difficulties_encountered') and memory.difficulties_encountered:
                    context_parts.append(f"- 你之前遇到过：{', '.join(memory.difficulties_encountered[:2])}")
                if hasattr(memory, 'reflection') and memory.reflection and len(memory.reflection) > 20:
                    context_parts.append(f"- 你之前的反思：{memory.reflection[:100]}...")
            
            return "\n".join(context_parts)
        except Exception as e:
            logging.warning(f"构建个人上下文失败: {e}")
            return f"你是{self.student.student_type.value}类型的学生"
    
    def _generate_fallback_reflection(self, feedback_summary: Dict[str, Any], improvement_context: str) -> str:
        """生成后备的反思内容（当LLM生成的反思不足时）"""
        areas = feedback_summary.get('areas_to_improve', ['相关问题'])[:2]
        if not areas:  # 确保areas不为空
            areas = ['相关问题']
        avg_score = feedback_summary.get('average_score', 75)
        
        reflection = f"这次修改让我意识到了{areas[0]}的重要性。"
        
        if avg_score < 70:
            reflection += f"虽然平均只得了{avg_score:.1f}分，但我通过同伴的反馈看到了自己在{', '.join(areas)}方面的不足。"
        else:
            reflection += f"虽然平均分{avg_score:.1f}分还算可以，但我发现在{', '.join(areas)}方面还有提升空间。"
        
        if "经验" in improvement_context:
            reflection += "回顾过往的学习经历，我发现这些问题其实之前也出现过，说明我需要建立更系统的学习方法。"
        else:
            reflection += "这是我第一次在这类问题上收到详细反馈，让我对自己的弱点有了更清晰的认识。"
        
        reflection += f"下次类似的作业中，我会特别注意{areas[0]}，并且在提交前多检查几遍。"
        
        return reflection
    
    def _calculate_improvement_score(self, original_work: StudentWork, 
                                    sections: Dict[str, str], 
                                    feedback_summary: Dict[str, Any]) -> float:
        """计算改进程度评分（0-1之间）"""
        score = 0.5  # 基础分
        
        # 1. 检查改进说明的详细程度
        improvement_desc = sections.get("改进说明", "")
        if len(improvement_desc) > 100:
            score += 0.15
        elif len(improvement_desc) > 50:
            score += 0.05
        
        # 2. 检查深度反思的质量
        reflection = sections.get("深度反思", "")
        if len(reflection) > 80:
            score += 0.15
        elif len(reflection) > 50:
            score += 0.05
        
        # 3. 检查是否包含具体的改进点
        if any(keyword in improvement_desc for keyword in ["具体", "修改了", "改进了", "添加了", "优化了"]):
            score += 0.1
        
        # 4. 检查反思中是否有自我认知
        if any(keyword in reflection for keyword in ["意识到", "发现", "学到", "下次", "今后"]):
            score += 0.1
        
        return min(1.0, max(0.3, score))
    
    def _calculate_personalized_score(self, original_score: float, 
                                      improvement_score: float, 
                                      feedback_avg: float) -> float:
        """计算个性化的修改后分数（而非统一75分）"""
        # 基础分：反馈平均分
        base_score = feedback_avg
        
        # 根据改进程度调整
        if improvement_score > 0.8:
            # 高质量改进：+15-25分
            bonus = 15 + (improvement_score - 0.8) * 50
        elif improvement_score > 0.6:
            # 中等改进：+10-15分
            bonus = 10 + (improvement_score - 0.6) * 25
        elif improvement_score > 0.4:
            # 基础改进：+5-10分
            bonus = 5 + (improvement_score - 0.4) * 25
        else:
            # 改进不足：+0-5分
            bonus = improvement_score * 12.5
        
        final_score = min(95, base_score + bonus)  # 最高不超过95分
        
        return final_score
    
    def _generate_default_revision_reflection(self, feedback_summary: Dict[str, Any], 
                                              round_number: int, 
                                              improvement_score: float) -> str:
        """生成默认的修订反思（当LLM生成失败时）"""
        areas = feedback_summary.get('areas_to_improve', ['多个方面'])[:2]
        if not areas:  # 确保areas不为空
            areas = ['多个方面']
        avg_score = feedback_summary.get('average_score', 75)
        
        # 根据改进程度选择不同的反思模板
        if improvement_score > 0.7:
            reflection = f"第{round_number}轮修改中，我认真分析了同伴指出的{', '.join(areas)}等问题，"
            reflection += f"通过重新审视原代码，我发现这些问题确实存在。"
            reflection += f"这次经历让我意识到，{areas[0]}是我一直以来的薄弱环节，"
            reflection += f"可能和我平时学习时过于注重完成任务而忽视质量有关。"
            reflection += f"今后我会在提交前增加自我检查环节，特别关注{areas[0]}的完整性。"
        elif improvement_score > 0.5:
            reflection = f"收到第{round_number}轮反馈（平均{avg_score:.1f}分）后，我尝试改进了{', '.join(areas)}。"
            reflection += f"虽然知道问题所在，但改起来还是有些吃力，说明我对这些知识点的掌握还不够扎实。"
            reflection += f"这提醒我不能只满足于表面的理解，需要深入学习{areas[0]}的原理和应用场景。"
        else:
            reflection = f"第{round_number}轮修改：针对反馈改进了{', '.join(areas)}，"
            reflection += f"但说实话改进得比较仓促。收到{avg_score:.1f}分的评价确实让我有些慌乱，"
            reflection += f"可能还是老毛病——赶在截止日期前匆忙应付。下次得改改这个习惯了。"
        
        return reflection
    
    def _store_revision_memory(self, original_work: StudentWork, revised_work: StudentWork,
                               feedback_summary: Dict[str, Any], round_number: int,
                               assignment: Assignment, revision_data: Dict[str, Any] = None):
        """存储作业修订的记忆（增强版：包含结构化反思和验证）"""
        try:
            importance = 0.7
            if feedback_summary.get('average_score', 75) < 70:
                importance += 0.1
            if len(feedback_summary.get('areas_to_improve', [])) >= 2:
                importance += 0.1
            importance = min(1.0, importance)
            
            # 从修订数据中提取深度反思
            deep_reflection = ""
            if revision_data:
                deep_reflection = revision_data.get('reflection', '')
                improvement_score = revision_data.get('improvement_score', 0.5)
            else:
                improvement_score = 0.5
            
            # 如果没有深度反思，生成默认反思
            if not deep_reflection or len(deep_reflection) < 50:
                deep_reflection = self._generate_default_revision_reflection(
                    feedback_summary, round_number, improvement_score
                )
            
            # 计算基于改进程度的个性化分数
            personalized_score = self._calculate_personalized_score(
                original_score=getattr(original_work, 'score', feedback_summary.get('average_score', 75)),
                improvement_score=improvement_score,
                feedback_avg=feedback_summary.get('average_score', 75)
            )
            
            revision_memory = LearningMemory(
                id=f"mem_revision_{revised_work.id}_{uuid.uuid4().hex[:8]}",
                content=f"根据第{round_number}轮反馈修改了{assignment.title}作业",
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                knowledge_points=assignment.knowledge_points_covered[:3],
                score=personalized_score,  # 使用个性化评分
                time_spent=(20 + round_number * 5) / 60.0,
                difficulty=assignment.difficulty_level,
                success=personalized_score >= 70,
                learning_from_peer=[f"改进了{area}" for area in feedback_summary.get('areas_to_improve', [])[:3]],
                reflection=deep_reflection,  # 使用深度反思
                importance=importance
            )
            
            self.new_memory_system.add_memory(revision_memory)
            
            logging.info(f"存储修订记忆：个性化分数={personalized_score:.1f}, 改进程度={improvement_score:.2f}, 反思字数={len(deep_reflection)}")
            logging.info(f"修订记忆已存储: {revision_memory.id}, importance={importance:.2f}")
        except Exception as e:
            logging.error(f"存储修订记忆失败: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        if self.use_new_memory:
            return self.new_memory_system.get_stats()
        return {}
