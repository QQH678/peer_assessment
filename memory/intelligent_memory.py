"""
增强学生记忆系统数据模型
集成智能记忆系统组件
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum
import json
import os
import logging

from .memory_base import MemoryEncoder, SimilarityCalculator, MemoryMetrics
from .case_library import Case, CaseLibrary
from .vector_retrieval import VectorRetrievalEngine
from .experience_replay import Experience, ExperienceReplay

class IntelligentMemoryState(BaseModel):
    """智能记忆状态"""
    student_id: str
    
    # 记忆组件状态
    encoder_config: Dict[str, Any] = Field(default_factory=dict, description="编码器配置")
    case_library_stats: Dict[str, Any] = Field(default_factory=dict, description="案例库统计")
    retrieval_engine_stats: Dict[str, Any] = Field(default_factory=dict, description="检索引擎统计")
    experience_replay_stats: Dict[str, Any] = Field(default_factory=dict, description="经验回放统计")
    
    # 记忆内容
    stored_cases: List[Dict[str, Any]] = Field(default_factory=list, description="存储的案例")
    experiences: List[Dict[str, Any]] = Field(default_factory=list, description="经验记录")
    knowledge_vectors: Dict[str, Any] = Field(default_factory=dict, description="知识点向量数据")
    
    # 短期和长期记忆（与Student模型同步）
    short_term_memory: Dict[str, Any] = Field(default_factory=dict, description="短期记忆")
    long_term_memory: Dict[str, Any] = Field(default_factory=dict, description="长期记忆")
    
    # 学习状态
    learning_progress: Dict[str, float] = Field(default_factory=dict, description="学习进度")
    concept_mastery: Dict[str, float] = Field(default_factory=dict, description="概念掌握度")
    memory_effectiveness: float = Field(default=0.0, description="记忆系统效果")
    last_memory_update: Optional[datetime] = Field(default=None, description="最后记忆更新时间")
    
    # 统计计数器
    total_retrievals: int = Field(default=0, description="总检索次数")
    total_replays: int = Field(default=0, description="总回放次数")
    last_retrieval: Optional[datetime] = Field(default=None, description="最后检索时间")
    last_replay: Optional[datetime] = Field(default=None, description="最后回放时间")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = self.model_dump()
        if self.last_memory_update:
            data['last_memory_update'] = self.last_memory_update.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IntelligentMemoryState':
        """从字典创建实例"""
        if 'last_memory_update' in data and isinstance(data['last_memory_update'], str):
            data['last_memory_update'] = datetime.fromisoformat(data['last_memory_update'])
        return cls(**data)

class MemoryContext(BaseModel):
    """记忆上下文"""
    knowledge_point_ids: List[str] = Field(description="相关知识点")
    difficulty_level: int = Field(description="难度级别")
    current_problem: str = Field(description="当前问题")
    available_resources: List[str] = Field(default_factory=list, description="可用资源")
    time_constraints: Optional[int] = Field(default=None, description="时间限制(分钟)")
    learning_objectives: List[str] = Field(default_factory=list, description="学习目标")

class MemoryRetrievalResult(BaseModel):
    """记忆检索结果"""
    retrieved_cases: List[Dict[str, Any]] = Field(description="检索到的案例")
    similarity_scores: List[float] = Field(description="相似度分数")
    retrieval_time_ms: float = Field(description="检索耗时")
    confidence_level: float = Field(description="置信度")
    explanation: str = Field(description="检索解释")

class LearningOutcome(BaseModel):
    """学习结果"""
    success: bool = Field(description="是否成功")
    score: float = Field(description="得分")
    concepts_learned: List[str] = Field(description="学到的概念")
    concepts_reinforced: List[str] = Field(description="强化的概念")
    errors_made: List[str] = Field(default_factory=list, description="犯的错误")
    time_spent: int = Field(description="花费时间(分钟)")
    reflection: str = Field(default="", description="反思总结")

class StudentMemorySystem:
    """学生智能记忆系统"""
    
    def __init__(self, student_id: str, config: Dict[str, Any] = None):
        self.student_id = student_id
        self.config = config or {}
        
        # 初始化记忆组件
        self.encoder = MemoryEncoder()
        self.similarity_calculator = SimilarityCalculator()
        self.metrics = MemoryMetrics()
        
        self.case_library = CaseLibrary(self.encoder)
        self.retrieval_engine = VectorRetrievalEngine(
            encoder=self.encoder,
            index_dimension=self.config.get('index_dimension', 100),
            cache_size=self.config.get('cache_size', 1000)
        )
        self.experience_replay = ExperienceReplay(
            buffer_size=self.config.get('buffer_size', 5000),
            default_batch_size=self.config.get('batch_size', 16)
        )
        
        # 记忆状态
        self.memory_state = IntelligentMemoryState(student_id=student_id)
        
        # 学习历史
        self.learning_sessions = []
        self.concept_network = {}  # 概念关联网络
        
    def store_learning_experience(self, 
                                 problem: str,
                                 solution: str,
                                 context: MemoryContext,
                                 outcome: LearningOutcome) -> str:
        """存储学习经验"""
        
        # 创建案例
        case_id = f"{self.student_id}_{len(self.memory_state.stored_cases)}"
        case = Case(
            id=case_id,
            problem_description=problem,
            solution=solution,
            context=context.model_dump(),
            outcome=outcome.model_dump(),
            timestamp=datetime.now(),
            tags=context.knowledge_point_ids,
            difficulty_level=context.difficulty_level,
            success_score=outcome.score / 100.0 if outcome.success else 0.0
        )
        
        # 添加到案例库
        self.case_library.add_case(case)
        
        # 添加到检索引擎
        self.retrieval_engine.add_case(case)
        
        # 编码为知识向量（长期记忆）
        knowledge_vector = self.encoder.encode_concepts(f"{problem} {solution}")
        self.memory_state.knowledge_vectors[case_id] = knowledge_vector.tolist()
        
        # 创建经验
        experience_id = f"exp_{case_id}"
        self.experience_replay.add_experience(
            experience_id=experience_id,
            content={
                "problem": problem,
                "solution": solution,
                "case_id": case_id
            },
            context=context.model_dump(),
            outcome=outcome.model_dump(),
            importance=self._calculate_importance(outcome, context),
            success_score=outcome.score / 100.0 if outcome.success else 0.0,
            tags=context.knowledge_point_ids
        )
        
        # 更新记忆状态
        self.memory_state.stored_cases.append(case.to_dict())
        self.memory_state.experiences.append({
            "id": experience_id,
            "case_id": case_id,
            "timestamp": datetime.now().isoformat(),
            "importance": self._calculate_importance(outcome, context)
        })
        
        # 更新概念掌握度
        self._update_concept_mastery(context.knowledge_point_ids, outcome)
        
        # 更新概念网络
        self._update_concept_network(context.knowledge_point_ids, outcome.success)
        
        # 更新短期和长期记忆
        self._update_memory_systems(context, outcome)
        
        # 更新学习进度
        self._update_learning_progress(context.knowledge_point_ids, outcome)
        
        # 更新统计信息
        self._update_statistics()
        
        # 记录学习会话
        self._record_learning_session(case_id, context, outcome)
        
        self.memory_state.last_memory_update = datetime.now()
        
        return case_id
    
    def retrieve_relevant_cases(self, 
                               current_problem: str,
                               context: MemoryContext,
                               max_cases: int = 5) -> MemoryRetrievalResult:
        """检索相关案例"""
        
        start_time = datetime.now()
        
        # 使用混合搜索
        results = self.retrieval_engine.hybrid_search(
            query=current_problem,
            keywords=context.knowledge_point_ids,
            filters={
                'difficulty_range': (max(1, context.difficulty_level - 1), 
                                   min(5, context.difficulty_level + 1)),
                'min_success_score': 0.3
            },
            top_k=max_cases
        )
        
        retrieval_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # 提取案例和分数
        retrieved_cases = []
        similarity_scores = []
        
        for case_id, similarity, metadata in results:
            case = self.case_library.get_case_by_id(case_id)
            if case:
                retrieved_cases.append(case.to_dict())
                similarity_scores.append(similarity)
        
        # 计算置信度
        confidence = np.mean(similarity_scores) if similarity_scores else 0.0
        
        # 生成解释
        explanation = self._generate_retrieval_explanation(
            len(retrieved_cases), 
            confidence, 
            context.knowledge_point_ids
        )
        
        # 更新检索统计
        self.memory_state.total_retrievals += 1
        self.memory_state.last_retrieval = datetime.now()
        
        return MemoryRetrievalResult(
            retrieved_cases=retrieved_cases,
            similarity_scores=similarity_scores,
            retrieval_time_ms=retrieval_time,
            confidence_level=confidence,
            explanation=explanation
        )
    
    def trigger_experience_replay(self, 
                                 learning_context: MemoryContext,
                                 replay_strategy: str = "mixed") -> Dict[str, Any]:
        """触发经验回放"""
        
        def learning_callback(experience: Experience) -> Dict[str, Any]:
            """学习回调函数"""
            try:
                # 强化相关概念的掌握度
                tags = experience.tags
                importance_boost = experience.importance * 0.1
                
                for tag in tags:
                    if tag in self.memory_state.concept_mastery:
                        self.memory_state.concept_mastery[tag] = min(
                            1.0, 
                            self.memory_state.concept_mastery[tag] + importance_boost
                        )
                
                # 更新概念网络连接强度
                self._strengthen_concept_connections(tags)
                
                return {"success": True, "concepts_reinforced": tags}
            
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        # 执行经验回放
        if replay_strategy == "contextual":
            # 基于当前上下文的回放
            replay_result = self.experience_replay.replay_by_tags(
                tags=learning_context.knowledge_point_ids,
                learning_callback=learning_callback
            )
        else:
            # 常规回放
            replay_result = self.experience_replay.replay_session(
                sampling_method=replay_strategy,
                learning_callback=learning_callback
            )
        
        # 更新记忆效果和回放统计
        self.memory_state.memory_effectiveness = replay_result.get("effectiveness", 0.0)
        self.memory_state.total_replays += 1
        self.memory_state.last_replay = datetime.now()
        
        return replay_result
    
    def get_learning_recommendations(self, 
                                   current_context: MemoryContext) -> List[Dict[str, Any]]:
        """获取学习建议"""
        
        recommendations = []
        
        # 基于概念掌握度的建议
        weak_concepts = [
            concept for concept, mastery in self.memory_state.concept_mastery.items()
            if mastery < 0.6 and concept in current_context.knowledge_point_ids
        ]
        
        if weak_concepts:
            # 为薄弱概念推荐案例
            for concept in weak_concepts:
                concept_cases = self.retrieval_engine.hybrid_search(
                    query="",
                    keywords=[concept],
                    filters={'min_success_score': 0.7},
                    top_k=3
                )
                
                if concept_cases:
                    recommendations.append({
                        "type": "concept_reinforcement",
                        "concept": concept,
                        "mastery_level": self.memory_state.concept_mastery[concept],
                        "recommended_cases": [case_id for case_id, _, _ in concept_cases],
                        "priority": "high" if self.memory_state.concept_mastery[concept] < 0.4 else "medium"
                    })
        
        # 基于经验回放的建议
        replay_stats = self.experience_replay.get_statistics()
        if replay_stats["total_experiences_learned"] > 0:
            if replay_stats["average_learning_effectiveness"] < 0.5:
                recommendations.append({
                    "type": "review_session",
                    "description": "建议进行经验回放复习",
                    "target_concepts": current_context.knowledge_point_ids,
                    "priority": "medium"
                })
        
        # 基于概念网络的建议
        related_concepts = self._get_related_concepts(current_context.knowledge_point_ids)
        if related_concepts:
            recommendations.append({
                "type": "concept_expansion",
                "description": "建议学习相关概念",
                "related_concepts": related_concepts,
                "priority": "low"
            })
        
        return recommendations
    
    def _calculate_importance(self, outcome: LearningOutcome, context: MemoryContext) -> float:
        """计算经验重要性"""
        base_importance = 0.5
        
        # 基于结果调整
        if outcome.success:
            base_importance += 0.2
        
        # 基于难度调整
        difficulty_factor = context.difficulty_level / 5.0
        base_importance += difficulty_factor * 0.2
        
        # 基于错误学习价值
        if outcome.errors_made:
            base_importance += len(outcome.errors_made) * 0.1
        
        # 基于概念覆盖度
        concept_coverage = len(context.knowledge_point_ids) / 10.0  # 假设最多10个概念
        base_importance += concept_coverage * 0.1
        
        return min(1.0, base_importance)
    
    def _update_concept_mastery(self, concepts: List[str], outcome: LearningOutcome):
        """更新概念掌握度"""
        success_boost = 0.1 if outcome.success else -0.05
        
        for concept in concepts:
            current_mastery = self.memory_state.concept_mastery.get(concept, 0.0)
            
            # 基于学习结果调整
            new_mastery = current_mastery + success_boost
            
            # 基于学到的概念额外奖励
            if concept in outcome.concepts_learned:
                new_mastery += 0.15
            
            # 基于强化的概念额外奖励
            if concept in outcome.concepts_reinforced:
                new_mastery += 0.05
            
            # 限制在[0, 1]范围
            self.memory_state.concept_mastery[concept] = max(0.0, min(1.0, new_mastery))
    
    def _update_concept_network(self, concepts: List[str], success: bool):
        """更新概念关联网络"""
        weight_change = 0.1 if success else -0.02
        
        # 更新概念之间的关联强度
        for i, concept1 in enumerate(concepts):
            if concept1 not in self.concept_network:
                self.concept_network[concept1] = {}
            
            for j, concept2 in enumerate(concepts):
                if i != j:
                    current_weight = self.concept_network[concept1].get(concept2, 0.0)
                    new_weight = max(0.0, min(1.0, current_weight + weight_change))
                    self.concept_network[concept1][concept2] = new_weight
    
    def _strengthen_concept_connections(self, concepts: List[str]):
        """强化概念连接"""
        for concept in concepts:
            if concept in self.concept_network:
                for related_concept in self.concept_network[concept]:
                    current_strength = self.concept_network[concept][related_concept]
                    self.concept_network[concept][related_concept] = min(
                        1.0, current_strength + 0.05
                    )
    
    def _get_related_concepts(self, concepts: List[str]) -> List[str]:
        """获取相关概念"""
        related = set()
        
        for concept in concepts:
            if concept in self.concept_network:
                for related_concept, strength in self.concept_network[concept].items():
                    if strength > 0.5:  # 强关联阈值
                        related.add(related_concept)
        
        return list(related - set(concepts))  # 排除已有概念
    
    def _generate_retrieval_explanation(self, 
                                      num_cases: int, 
                                      confidence: float, 
                                      concepts: List[str]) -> str:
        """生成检索解释"""
        if num_cases == 0:
            return "未找到相关案例，建议寻求帮助或学习基础概念。"
        
        if confidence > 0.8:
            return f"找到 {num_cases} 个高度相关的案例，建议仔细研究这些成功经验。"
        elif confidence > 0.6:
            return f"找到 {num_cases} 个相关案例，可以作为参考，但需要结合当前情况调整。"
        else:
            return f"找到 {num_cases} 个相关案例，相关性一般，建议作为启发思路使用。"
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取记忆系统统计信息"""
        # 更新统计信息
        self._update_statistics()
        
        # 使用记忆状态中的统计信息，而不是重新计算
        case_stats = self.memory_state.case_library_stats if self.memory_state.case_library_stats else self.case_library.get_statistics()
        retrieval_stats = self.memory_state.retrieval_engine_stats if self.memory_state.retrieval_engine_stats else self.retrieval_engine.get_statistics()
        replay_stats = self.memory_state.experience_replay_stats if self.memory_state.experience_replay_stats else self.experience_replay.get_statistics()
        
        # 补充额外的统计信息
        additional_stats = {
            "assignments_completed": len(self.learning_sessions),
            "average_performance": np.mean([session.get("score", 0) for session in self.learning_sessions]) if self.learning_sessions else 0.0,
            "memory_usage_frequency": sum(1 for session in self.learning_sessions if session.get("used_memory", False)),
            "learning_effectiveness": self.memory_state.memory_effectiveness
        }
        
        return {
            "student_id": self.student_id,
            "case_library": case_stats,
            "retrieval_engine": retrieval_stats,
            "experience_replay": replay_stats,
            "concept_mastery_avg": np.mean(list(self.memory_state.concept_mastery.values())) 
                                  if self.memory_state.concept_mastery else 0.0,
            "memory_effectiveness": self.memory_state.memory_effectiveness,
            "concept_network_density": len(self.concept_network),
            "last_update": self.memory_state.last_memory_update.isoformat() 
                          if self.memory_state.last_memory_update else None,
            **additional_stats
        }
    
    def sync_from_student(self, student):
        """
        从Student对象同步short/long_term_memory到IntelligentMemoryState
        
        Args:
            student: Student对象，包含short_term_memory和long_term_memory
        """
        if hasattr(student, 'short_term_memory'):
            self.memory_state.short_term_memory = student.short_term_memory
        if hasattr(student, 'long_term_memory'):
            self.memory_state.long_term_memory = student.long_term_memory
        
        logging.debug(f"Synced memory from student {self.student_id}: "
                     f"STM keys={len(self.memory_state.short_term_memory)}, "
                     f"LTM keys={len(self.memory_state.long_term_memory)}")
    
    def sync_to_student(self, student):
        """
        从IntelligentMemoryState同步short/long_term_memory到Student对象
        
        Args:
            student: Student对象，将更新其short_term_memory和long_term_memory
        """
        if hasattr(student, 'short_term_memory'):
            student.short_term_memory = self.memory_state.short_term_memory
        if hasattr(student, 'long_term_memory'):
            student.long_term_memory = self.memory_state.long_term_memory
        
        logging.debug(f"Synced memory to student {self.student_id}: "
                     f"STM keys={len(self.memory_state.short_term_memory)}, "
                     f"LTM keys={len(self.memory_state.long_term_memory)}")
    
    def save_memory_state(self, filepath: str):
        """保存记忆状态"""
        def datetime_serializer(obj):
            """自定义JSON序列化器，处理datetime和numpy对象"""
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, 'tolist'):  # numpy数组
                return obj.tolist()
            elif hasattr(obj, 'item'):  # numpy标量
                return obj.item()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        state_data = {
            "memory_state": self.memory_state.to_dict(),
            "concept_network": self.concept_network,
            "learning_sessions": self.learning_sessions,
            "saved_at": datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=2, default=datetime_serializer)
        
        # 保存检索引擎索引
        index_filepath = filepath.replace('.json', '_index.pkl')
        self.retrieval_engine.save_index(index_filepath)
    
    def load_memory_state(self, filepath: str):
        """加载记忆状态"""
        # 检查文件是否存在
        if not os.path.exists(filepath):
            logging.info(f"记忆文件不存在，跳过加载: {filepath}")
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # 安全地重建记忆状态，处理验证错误
            try:
                self.memory_state = IntelligentMemoryState.from_dict(state_data["memory_state"])
            except Exception as e:
                logging.warning(f"记忆状态验证失败，使用修复后的数据: {e}")
                # 修复知识向量数据类型问题
                memory_state_data = state_data["memory_state"].copy()
                
                # 如果knowledge_vectors包含非列表数据，保持原样
                if "knowledge_vectors" in memory_state_data:
                    # 不强制转换，允许字典格式
                    pass
                
                # 创建新的记忆状态
                self.memory_state = IntelligentMemoryState()
                
                # 安全地复制数据
                for key, value in memory_state_data.items():
                    if hasattr(self.memory_state, key):
                        try:
                            setattr(self.memory_state, key, value)
                        except Exception as set_error:
                            logging.warning(f"跳过字段 {key}: {set_error}")
                            continue
            
            self.concept_network = state_data.get("concept_network", {})
            self.learning_sessions = state_data.get("learning_sessions", [])
            
            # 重建案例库和经验
            for case_data in self.memory_state.stored_cases:
                try:
                    case = Case.from_dict(case_data)
                    self.case_library.add_case(case)
                    self.retrieval_engine.add_case(case)
                except Exception as e:
                    logging.warning(f"跳过损坏的案例数据: {e}")
                    continue
            
            for exp_data in self.memory_state.experiences:
                try:
                    if 'case_id' in exp_data:
                        case = self.case_library.get_case_by_id(exp_data['case_id'])
                        if case:
                            self.experience_replay.add_experience(
                                experience_id=exp_data['id'],
                                content={"case_id": exp_data['case_id']},
                                context=case.context,
                                outcome=case.outcome,
                                importance=exp_data.get('importance', 0.5),
                                success_score=case.success_score
                            )
                except Exception as e:
                    logging.warning(f"跳过损坏的经验数据: {e}")
                    continue
            
            # 加载检索引擎索引
            index_filepath = filepath.replace('.json', '_index.pkl')
            self.retrieval_engine.load_index(index_filepath)
            
        except FileNotFoundError:
            # 首次运行，使用默认状态
            pass
        except Exception as e:
            print(f"Error loading memory state: {e}")

    def _update_memory_systems(self, context: MemoryContext, outcome: LearningOutcome):
        """更新短期和长期记忆系统"""
        # 更新短期记忆：最近学习的概念
        for concept in context.knowledge_point_ids:
            if concept not in self.memory_state.knowledge_vectors:
                self.memory_state.knowledge_vectors[concept] = {
                    "short_term_strength": 0.0,
                    "long_term_strength": 0.0,
                    "last_accessed": datetime.now().isoformat(),
                    "access_count": 0,
                    "success_rate": 0.0
                }
            
            # 🔧 修复：基于实际学习表现动态计算记忆强度增量
            current_strength = self.memory_state.knowledge_vectors[concept]["short_term_strength"]
            
            # 计算基础增量（基于得分）
            # score范围0-100，归一化到0-1，再映射到0.1-0.5的增量范围
            normalized_score = outcome.score / 100.0
            base_increment = 0.1 + (normalized_score * 0.4)  # 0.1-0.5之间
            
            # 难度系数：难题记忆更深刻（难度1-5）
            difficulty_factor = 1.0 + (context.difficulty_level - 3) * 0.1  # 0.8-1.2之间
            
            # 成功/失败调整
            if outcome.success:
                # 成功：正常增量
                strength_increment = base_increment * difficulty_factor
            else:
                # 失败：减少增量，但仍有学习效果
                strength_increment = base_increment * difficulty_factor * 0.3
            
            self.memory_state.knowledge_vectors[concept]["short_term_strength"] = min(1.0, current_strength + strength_increment)
            
            # 更新访问计数和成功率
            self.memory_state.knowledge_vectors[concept]["access_count"] += 1
            self.memory_state.knowledge_vectors[concept]["last_accessed"] = datetime.now().isoformat()
            
            # 🔧 修复：动态更新成功率（增量式计算，避免全量遍历）
            kv = self.memory_state.knowledge_vectors[concept]
            total_accesses = kv["access_count"]
            if total_accesses == 1:
                # 首次访问
                kv["success_rate"] = 1.0 if outcome.success else 0.0
            else:
                # 增量更新：(旧成功率 * (n-1) + 新结果) / n
                old_success_rate = kv["success_rate"]
                new_result = 1.0 if outcome.success else 0.0
                kv["success_rate"] = (old_success_rate * (total_accesses - 1) + new_result) / total_accesses
        
        # 短期记忆向长期记忆转化
        for concept in context.knowledge_point_ids:
            if concept in self.memory_state.knowledge_vectors:
                kv = self.memory_state.knowledge_vectors[concept]
                
                # 🔧 修复：降低转化条件，使其更容易形成长期记忆
                # 条件1: 短期记忆强度超过0.5（原来0.7，太高）
                # 条件2: 访问次数达到2次（原来3次，太高）
                if kv["short_term_strength"] > 0.5 and kv["access_count"] >= 2:
                    # 巩固到长期记忆
                    # 🔧 提高转化率：从0.1提高到0.2
                    transfer_rate = min(0.2, kv["short_term_strength"] * 0.15)
                    kv["long_term_strength"] = min(1.0, kv["long_term_strength"] + transfer_rate)
                    # 短期记忆衰减更慢，保持学习连续性
                    kv["short_term_strength"] = max(0.0, kv["short_term_strength"] - transfer_rate * 0.5)
                
                # 🔧 新增：即使条件不满足，也有微量转化（模拟自然记忆形成）
                elif kv["access_count"] >= 1 and kv["short_term_strength"] > 0.2:
                    # 轻微转化到长期记忆
                    gentle_transfer = kv["short_term_strength"] * 0.05
                    kv["long_term_strength"] = min(1.0, kv["long_term_strength"] + gentle_transfer)

    def _update_learning_progress(self, knowledge_point_ids: List[str], outcome: LearningOutcome):
        """更新学习进度"""
        for concept in knowledge_point_ids:
            if concept not in self.memory_state.learning_progress:
                self.memory_state.learning_progress[concept] = 0.0
            
            # 基于学习成果更新进度
            progress_increment = 0.0
            if outcome.success:
                progress_increment = 0.2  # 成功学习增加20%
            else:
                progress_increment = 0.05  # 尝试学习增加5%
            
            # 考虑花费时间的影响
            if outcome.time_spent > 0:
                time_factor = min(1.0, outcome.time_spent / 60.0)  # 标准化到小时
                progress_increment *= (0.5 + 0.5 * time_factor)  # 时间投入影响进度
            
            self.memory_state.learning_progress[concept] = min(1.0, 
                self.memory_state.learning_progress[concept] + progress_increment)

    def _update_statistics(self):
        """更新统计信息"""
        # 更新案例库统计
        total_cases = len(self.memory_state.stored_cases)
        successful_cases = sum(1 for case in self.memory_state.stored_cases 
                             if case.get("outcome", {}).get("success", False))
        
        self.memory_state.encoder_config = {
            "vector_dimension": 100,
            "encoding_method": "tfidf",
            "last_updated": datetime.now().isoformat()
        }
        
        self.memory_state.case_library_stats = {
            "total_cases": total_cases,
            "successful_cases": successful_cases,
            "success_rate": successful_cases / total_cases if total_cases > 0 else 0.0,
            "average_difficulty": sum(case.get("difficulty_level", 0) for case in self.memory_state.stored_cases) / total_cases if total_cases > 0 else 0.0,
            "most_frequent_concepts": self._get_most_frequent_concepts()
        }
        
        self.memory_state.retrieval_engine_stats = {
            "total_retrievals": self.memory_state.total_retrievals,
            "average_retrieval_time_ms": getattr(self, '_avg_retrieval_time', 0.0),
            "index_size": total_cases,
            "last_retrieval": self.memory_state.last_retrieval.isoformat() if self.memory_state.last_retrieval else datetime.now().isoformat()
        }
        
        self.memory_state.experience_replay_stats = {
            "total_experiences": len(self.memory_state.experiences),
            "total_replays": self.memory_state.total_replays,
            "average_importance": sum(exp.get("importance", 0) for exp in self.memory_state.experiences) / len(self.memory_state.experiences) if self.memory_state.experiences else 0.0,
            "last_replay": self.memory_state.last_replay.isoformat() if self.memory_state.last_replay else datetime.now().isoformat()
        }
        
        # 计算记忆效能
        if total_cases > 0:
            mastery_avg = sum(self.memory_state.concept_mastery.values()) / len(self.memory_state.concept_mastery) if self.memory_state.concept_mastery else 0.0
            progress_avg = sum(self.memory_state.learning_progress.values()) / len(self.memory_state.learning_progress) if self.memory_state.learning_progress else 0.0
            self.memory_state.memory_effectiveness = (mastery_avg + progress_avg + (successful_cases / total_cases)) / 3.0

    def _get_most_frequent_concepts(self) -> List[str]:
        """获取最常见的概念"""
        concept_counts = {}
        for case in self.memory_state.stored_cases:
            for tag in case.get("tags", []):
                concept_counts[tag] = concept_counts.get(tag, 0) + 1
        
        return sorted(concept_counts.keys(), key=lambda x: concept_counts[x], reverse=True)[:5]

    def _record_learning_session(self, case_id: str, context: MemoryContext, outcome: LearningOutcome):
        """记录学习会话"""
        session = {
            "session_id": f"session_{case_id}",
            "start_time": datetime.now().isoformat(),
            "case_id": case_id,
            "knowledge_points": context.knowledge_point_ids,
            "difficulty_level": context.difficulty_level,
            "time_spent": outcome.time_spent,
            "success": outcome.success,
            "score": outcome.score,
            "concepts_learned": outcome.concepts_learned,
            "errors_made": outcome.errors_made,
            "reflection": outcome.reflection
        }
        
        self.learning_sessions.append(session)
        
        # 保持最近50个会话
        if len(self.learning_sessions) > 50:
            self.learning_sessions = self.learning_sessions[-50:]
    
    def _sync_case_to_experience(self, case: Case) -> 'Experience':
        """将案例同步为经验数据"""
        from memory.experience_replay import Experience
        
        experience = Experience(
            id=f"exp_{case.id}",
            content={
                "problem": case.problem_description,
                "solution": case.solution,
                "case_id": case.id
            },
            context={
                "tags": case.tags,
                "difficulty_level": case.difficulty_level,
                "student_type": "unknown",  # Case没有metadata，使用默认值
                "course": "unknown"
            },
            outcome={
                "success_score": case.success_score,
                "performance_score": case.success_score  # 使用success_score作为性能分数
            },
            timestamp=case.timestamp,
            importance=case.success_score,
            success_score=case.success_score,
            tags=case.tags
        )
        return experience

    def sync_data_sources(self):
        """同步案例库和经验缓冲区的数据"""
        synced_count = 0
        
        for case in self.case_library.cases.values():
            experience = self._sync_case_to_experience(case)
            
            if experience.id not in self.experience_replay.buffer.experiences:
                self.experience_replay.buffer.add(experience)
                synced_count += 1
        
        logging.info(f"Synced {synced_count} cases to experience buffer")
        return synced_count

    def trigger_experience_replay_enhanced(self, 
                                         learning_context: 'MemoryContext',
                                         replay_strategy: str = "contextual") -> Dict[str, Any]:
        """增强版经验回放，结合检索结果"""
        
        # 首先同步数据
        self.sync_data_sources()
        
        # 尝试检索相关案例
        try:
            retrieval_result = self.retrieve_relevant_cases(
                current_problem=f"Knowledge points: {', '.join(learning_context.knowledge_point_ids)}",
                context=learning_context,
                max_cases=5
            )
            
            # 如果检索到案例，优先使用这些经验
            if retrieval_result.retrieved_cases:
                case_ids = [case.get("id") for case in retrieval_result.retrieved_cases]
                experience_ids = [f"exp_{case_id}" for case_id in case_ids]
                
                relevant_experiences = []
                for exp_id in experience_ids:
                    if exp_id in self.experience_replay.buffer.experiences:
                        relevant_experiences.append(self.experience_replay.buffer.experiences[exp_id])
                
                if relevant_experiences:
                    return self._replay_specific_experiences(relevant_experiences, learning_context)
        
        except Exception as e:
            logging.warning(f"Retrieval failed, using fallback replay: {e}")
        
        # 回退到原有的经验回放
        return self.trigger_experience_replay(learning_context, replay_strategy)

    def _replay_specific_experiences(self, experiences: List['Experience'], 
                                   context: 'MemoryContext') -> Dict[str, Any]:
        """回放指定的经验列表"""
        
        def learning_callback(experience):
            try:
                importance_boost = experience.importance * 0.15
                for tag in experience.tags:
                    if tag in self.memory_state.concept_mastery:
                        self.memory_state.concept_mastery[tag] = min(
                            1.0, 
                            self.memory_state.concept_mastery[tag] + importance_boost
                        )
                return {"success": True, "concepts_reinforced": experience.tags}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        learning_results = []
        for experience in experiences:
            experience.increment_replay()
            result = learning_callback(experience)
            learning_results.append(result)
        
        successful_learning = sum(1 for result in learning_results if result.get("success", False))
        effectiveness = successful_learning / len(experiences) if experiences else 0.0
        
        # 更新回放统计
        self.memory_state.total_replays += 1
        self.memory_state.last_replay = datetime.now()
        self.memory_state.memory_effectiveness = effectiveness
        
        return {
            "experiences_learned": len(experiences),
            "successful_learning": successful_learning,
            "effectiveness": effectiveness,
            "strategy": "retrieval_based",
            "timestamp": datetime.now().isoformat()
        }

    def get_memory_statistics_enhanced(self) -> Dict[str, Any]:
        """增强版统计信息，显示数据同步状态"""
        
        # 获取原有统计
        stats = self.get_memory_statistics()
        
        # 添加数据同步信息
        case_count = len(self.case_library.cases)
        experience_count = len(self.experience_replay.buffer.experiences)
        
        # 计算同步率
        case_based_experiences = sum(1 for exp_id in self.experience_replay.buffer.experiences.keys() 
                                   if exp_id.startswith("exp_"))
        sync_rate = case_based_experiences / case_count if case_count > 0 else 0.0
        
        stats["data_sync"] = {
            "case_count": case_count,
            "experience_count": experience_count,
            "case_based_experiences": case_based_experiences,
            "sync_rate": sync_rate,
            "is_synchronized": sync_rate > 0.8
        }
        
        return stats

import numpy as np