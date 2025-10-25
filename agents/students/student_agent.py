from typing import Dict, Any, List, Optional
import openai
from models.data_models import Student, StudentWork, Assignment, Course, KnowledgePoint
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
    """升级的学生代理，集成新一代三维记忆系统"""
    
    def __init__(self, student: Student, memory_config: Dict[str, Any] = None, peer_review_config: Optional[PeerReviewConfig] = None):
        self.student = student
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        
        # 互评配置
        self.peer_review_config = peer_review_config or PeerReviewConfig()
        
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
        
        # 性能跟踪
        self.performance_metrics = {
            "assignments_completed": 0,
            "average_performance": 0.0,
            "memory_usage_frequency": 0,
            "learning_effectiveness": 0.0
        }
        
        logging.info(f"学生Agent初始化: {student.name}, 使用新记忆系统: {self.use_new_memory}")
    
    def complete_assignment(self, assignment: Assignment, course: Optional['Course'] = None) -> StudentWork:
        """使用智能记忆系统完成作业"""
        logging.info(f"开始完成作业 - 学生: {self.student.name}, 作业: {assignment.title}")
        start_time = datetime.now()
        
        # 构建记忆上下文
        logging.info(f"构建记忆上下文 - 学生: {self.student.name}")
        memory_context = self._build_memory_context(assignment, course)
        
        # 检索相关经验案例
        logging.info(f"检索相关经验案例 - 学生: {self.student.name}")
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
                {"role": "system", "content": self._get_enhanced_system_prompt()},
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
        
        # 更新传统记忆系统（保持兼容性）
        self._update_legacy_memory(assignment, work, course)
        
        # 使用新记忆系统存储学习记忆
        if self.use_new_memory:
            self._store_to_new_memory_system(assignment, work, learning_outcome, retrieval_result)
        
        logging.info(f"Assignment completed by {self.student.name} using intelligent memory system")
        
        return work
    
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
    
    def _get_enhanced_system_prompt(self) -> str:
        """获取增强的学生角色系统提示词"""
        basic_prompt = self._get_student_system_prompt()
        
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
        """估算作业表现水平 - 改进版，考虑学习进步和记忆效果"""
        # 提高基准表现，增加成功可能性
        base_performance = 0.72  # 提高基准表现，增加成功可能性
        
        # 根据学生类型调整 - 更合理的分布
        type_multipliers = {
            "excellent": 1.25,
            "good": 1.15,
            "average": 1.0,
            "below_average": 0.85,  # 提高低水平学生表现
            "strict": 1.05,
            "lenient": 0.95,
            "perfunctory": 0.8
        }
        
        performance = base_performance * type_multipliers.get(self.student.student_type.value, 0.9)
        
        # 考虑学习经验积累 - 渐进式改善
        assignments_completed = getattr(self.performance_metrics, 'assignments_completed', 0)
        learning_boost = min(0.15, assignments_completed * 0.03)  # 最多15%的提升
        performance += learning_boost
        
        # 根据记忆系统使用情况调整
        if hasattr(self.memory_system, 'case_library') and len(self.memory_system.case_library.cases) > 0:
            memory_boost = min(0.1, len(self.memory_system.case_library.cases) * 0.02)
            performance += memory_boost
        
        # 根据作业难度调整 - 更平滑的难度曲线
        difficulty_factor = max(0.6, 1.2 - 0.1 * assignment.difficulty_level)  # 减少难度惩罚
        performance *= difficulty_factor
        
        # 减少随机性，增加稳定性
        performance *= random.uniform(0.9, 1.15)
        
        return min(1.0, max(0.2, performance))
    
    
    def _get_student_system_prompt(self) -> str:
        """获取学生角色的系统提示词"""
        return f"""你是一名{self.student.major}专业的{self.student.academic_level}学生，名字叫{self.student.name}。

学生特征：
- 学生类型：{self.student.student_type.value}
- GPA：{self.student.gpa}
- 编程经验：{self.student.programming_experience}年
- 性格特征：{self.student.personality_traits}

请根据你的学术水平和能力特点来完成作业。如果你是优秀学生，作业应该质量很高；如果你是基础较弱的学生，作业可能存在一些问题或不完善的地方。

作业完成后，请按以下格式输出：
=== 作业内容 ===
[这里是你的作业内容，包括代码、设计等]

=== 文档说明 ===
[这里是你对作业的说明文档]

=== 预估工时 ===
[完成这个作业大概花费的小时数]

=== 自我评估 ===
功能实现: [0-100分]
代码质量: [0-100分] 
创新性: [0-100分]
文档完整性: [0-100分]
"""
    
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
        
        # 生成自我评估
        self_assessment = self._generate_self_assessment(sections.get("自我评估", ""))
        
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
        """解析LLM响应的结构化内容"""
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
    
    def _generate_self_assessment(self, assessment_text: str) -> Dict[str, int]:
        """生成自我评估分数"""
        import re
        
        # 尝试从文本中解析分数
        scores = {}
        dimensions = ["功能实现", "代码质量", "创新性", "文档完整性"]
        
        for dim in dimensions:
            pattern = f"{dim}[：:]\\s*(\\d+)"
            match = re.search(pattern, assessment_text)
            if match:
                scores[dim] = int(match.group(1))
            else:
                # 根据学生类型生成默认分数
                scores[dim] = self._get_default_self_score(dim)
        
        return scores
    
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
        """计算记忆重要性"""
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
        
        return min(1.0, importance)
    
    def evaluate_peer_work(self, peer_work: StudentWork, assignment: Assignment) -> Dict[str, Any]:
        """评价同伴作业"""
        logging.info(f"学生 {self.student.name} 开始评价 {peer_work.student_id} 的作业")
        
        # 构建评价提示词
        prompt = f"""你是一名{self.student.student_type.value}类型的学生，现在需要评价同伴的作业。

作业题目：{assignment.title}
作业描述：{assignment.description}
涉及知识点：{', '.join(assignment.knowledge_points_covered)}

同伴的作业内容：
{peer_work.content[:1000]}...

请从以下几个方面评价：
1. 功能实现（是否满足要求）
2. 代码质量（可读性、结构）
3. 创新性（是否有独特见解）
4. 文档完整性（注释、说明）

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
                importance=0.6 + (0.1 if len(learning_points) > 0 else 0)
            )
            
            self.new_memory_system.add_memory(peer_eval_memory)
            logging.info(f"评价记忆已添加: {peer_eval_memory.id}")
            
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
            
            # 存储被评价记忆
            if self.use_new_memory:
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
                    importance=0.7 + (0.2 if len(improvements) > 0 else 0)
                )
                
                self.new_memory_system.add_memory(received_memory)
                logging.info(f"被评价记忆已添加: {received_memory.id}")
                
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
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        if self.use_new_memory:
            return self.new_memory_system.get_stats()
        return {}
