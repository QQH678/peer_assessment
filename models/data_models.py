from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import json

class StudentType(str, Enum):
    """学生类型枚举"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    STRICT = "strict"
    LENIENT = "lenient"
    PERFUNCTORY = "perfunctory"

class AssignmentType(str, Enum):
    """作业类型枚举"""
    PROGRAMMING = "programming"
    PROJECT = "project"
    DESIGN_DOC = "design_doc"
    RESEARCH_REPORT = "research_report"

class MemoryType(str, Enum):
    """记忆类型枚举"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

class Student(BaseModel):
    """学生模型"""
    id: str
    name: str
    student_type: StudentType
    academic_level: str = Field(description="学术水平: undergraduate/graduate")
    major: str = Field(description="专业")
    gpa: float = Field(ge=0.0, le=4.0, description="GPA")
    programming_experience: int = Field(ge=0, description="编程经验(年)")
    personality_traits: Dict[str, float] = Field(description="性格特征")
    
    # 记忆系统
    short_term_memory: Dict[str, Any] = Field(default_factory=dict, description="短期记忆")
    long_term_memory: Dict[str, Any] = Field(default_factory=dict, description="长期记忆")
    knowledge_mastery: Dict[str, float] = Field(default_factory=dict, description="知识点掌握程度")
    performance_history: List[Dict[str, Any]] = Field(default_factory=list, description="历史表现记录")
    
    def to_dict(self) -> Dict[str, Any]:
        return safe_to_dict(self)
    
    def update_short_term_memory(self, key: str, value: Any, decay_factor: float = 0.1):
        """更新短期记忆，考虑遗忘曲线"""
        if key in self.short_term_memory:
            # 已存在的记忆会衰减
            old_value = self.short_term_memory[key]
            if isinstance(old_value, (int, float)) and isinstance(value, (int, float)):
                self.short_term_memory[key] = old_value * (1 - decay_factor) + value * decay_factor
            else:
                self.short_term_memory[key] = value
        else:
            self.short_term_memory[key] = value
    
    def update_long_term_memory(self, key: str, value: Any):
        """更新长期记忆"""
        self.long_term_memory[key] = value
    
    def consolidate_memory(self, knowledge_point_id: str, mastery_level: float):
        """将短期记忆转化为长期记忆"""
        if knowledge_point_id in self.short_term_memory:
            # 将短期记忆中的知识点转移到长期记忆
            self.long_term_memory[knowledge_point_id] = self.short_term_memory[knowledge_point_id]
            # 更新掌握程度
            self.knowledge_mastery[knowledge_point_id] = mastery_level
            # 减少短期记忆中的强度
            if isinstance(self.short_term_memory[knowledge_point_id], (int, float)):
                self.short_term_memory[knowledge_point_id] *= 0.5
    
    def get_knowledge_context(self, knowledge_point_ids: List[str]) -> Dict[str, Any]:
        """获取相关知识点的记忆上下文"""
        context = {
            "short_term": {},
            "long_term": {},
            "mastery_levels": {}
        }
        
        for kp_id in knowledge_point_ids:
            if kp_id in self.short_term_memory:
                context["short_term"][kp_id] = self.short_term_memory[kp_id]
            if kp_id in self.long_term_memory:
                context["long_term"][kp_id] = self.long_term_memory[kp_id]
            if kp_id in self.knowledge_mastery:
                context["mastery_levels"][kp_id] = self.knowledge_mastery[kp_id]
        
        return context

class Assignment(BaseModel):
    """作业模型"""
    id: str
    title: str
    description: str
    assignment_type: AssignmentType
    subject: str = Field(description="课程科目")
    course_type: str = Field(
        default="programming", 
        description="课程类型: programming/writing/design/theory/experiment/mathematics/generic"
    )
    difficulty_level: int = Field(ge=1, le=5, description="难度等级 1-5")
    requirements: List[str] = Field(description="具体要求")
    evaluation_criteria: Dict[str, str] = Field(description="评价标准")
    max_score: int = Field(default=100, description="最高分数")
    
    # 课程相关字段
    course_id: Optional[str] = Field(default=None, description="所属课程ID")
    stage_id: Optional[str] = Field(default=None, description="所属教学阶段ID")
    knowledge_points_covered: List[str] = Field(default_factory=list, description="涉及的知识点ID")
    estimated_hours: int = Field(default=8, description="预估完成时间")
    deliverables: List[str] = Field(default_factory=list, description="交付物")
    
    def to_dict(self) -> Dict[str, Any]:
        return safe_to_dict(self)

class StudentWork(BaseModel):
    """学生作品模型"""
    id: str
    student_id: str
    assignment_id: str
    content: str = Field(description="作品内容/代码")
    documentation: Optional[str] = Field(description="文档说明")
    submission_time: datetime
    estimated_effort_hours: int = Field(description="预估花费时间")
    self_assessment: Optional[Dict[str, int]] = Field(description="自我评估")
    
    def to_dict(self) -> Dict[str, Any]:
        return safe_to_dict(self)

class EvaluationScore(BaseModel):
    """评分详情（编程类 - 保留向后兼容）"""
    functionality: int = Field(ge=0, le=100, description="功能实现分数")
    code_quality: int = Field(ge=0, le=100, description="代码质量分数")
    innovation: int = Field(ge=0, le=100, description="创新性分数")
    documentation: int = Field(ge=0, le=100, description="文档完整性分数")
    
    # 通用评分字典（支持其他课程类型）
    dimension_scores: Optional[Dict[str, int]] = Field(
        default=None,
        description="通用评分维度: {维度key: 分数}"
    )
    
    def get_weighted_score(self, weights: Dict[str, float]) -> float:
        """计算加权总分"""
        # 如果有通用维度分数，优先使用
        if self.dimension_scores:
            total = 0.0
            for key, score in self.dimension_scores.items():
                total += score * weights.get(key, 1.0 / len(self.dimension_scores))
            return total
        
        # 否则使用编程类的固定维度
        return (
            self.functionality * weights.get("functionality", 0.4) +
            self.code_quality * weights.get("code_quality", 0.3) +
            self.innovation * weights.get("innovation", 0.15) +
            self.documentation * weights.get("documentation", 0.15)
        )
    
    def to_dict_generic(self) -> Dict[str, int]:
        """转换为通用字典格式"""
        if self.dimension_scores:
            return self.dimension_scores
        return {
            "functionality": self.functionality,
            "code_quality": self.code_quality,
            "innovation": self.innovation,
            "documentation": self.documentation
        }

class PeerEvaluation(BaseModel):
    """同伴互评模型"""
    id: str
    evaluator_id: str = Field(description="评价者ID")
    work_id: str = Field(description="被评价作品ID")
    assignment_id: str
    scores: EvaluationScore
    comments: Dict[str, str] = Field(description="各维度评价意见")
    overall_comment: str = Field(description="总体评价")
    evaluation_time: datetime
    time_spent_minutes: int = Field(description="评价花费时间(分钟)")
    
    def to_dict(self) -> Dict[str, Any]:
        return safe_to_dict(self)

class SimulationSession(BaseModel):
    """模拟会话模型"""
    session_id: str
    created_at: datetime
    parameters: Dict[str, Any] = Field(description="模拟参数")
    students: List[Student]
    assignments: List[Assignment]
    works: List[StudentWork]
    evaluations: List[PeerEvaluation]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_students": len(self.students),
            "total_assignments": len(self.assignments),
            "total_works": len(self.works),
            "total_evaluations": len(self.evaluations),
            "student_type_distribution": self._get_student_type_distribution(),
            "assignment_type_distribution": self._get_assignment_type_distribution()
        }
    
    def _get_student_type_distribution(self) -> Dict[str, int]:
        """获取学生类型分布"""
        distribution = {}
        for student in self.students:
            student_type = student.student_type.value
            distribution[student_type] = distribution.get(student_type, 0) + 1
        return distribution
    
    def _get_assignment_type_distribution(self) -> Dict[str, int]:
        """获取作业类型分布"""
        distribution = {}
        for assignment in self.assignments:
            assignment_type = assignment.assignment_type.value
            distribution[assignment_type] = distribution.get(assignment_type, 0) + 1
        return distribution

class KnowledgePoint(BaseModel):
    """知识点模型"""
    id: str
    name: str
    description: str
    difficulty_level: int = Field(ge=1, le=5, description="难度等级")
    prerequisites: List[str] = Field(default_factory=list, description="前置知识点ID")
    learning_objectives: List[str] = Field(description="学习目标")
    key_concepts: List[str] = Field(description="核心概念")
    estimated_hours: int = Field(description="预估学习时间")

class TeachingStage(BaseModel):
    """教学阶段模型"""
    stage_id: str
    name: str
    week_start: int = Field(description="开始周次")
    week_end: int = Field(description="结束周次")
    description: str = Field(description="阶段描述")
    knowledge_point_ids: List[str] = Field(description="包含的知识点ID")
    stage_objectives: List[str] = Field(description="阶段目标")
    assessment_focus: str = Field(description="评估重点")

class Course(BaseModel):
    """课程模型"""
    id: str
    name: str
    subject: str
    description: str
    duration_weeks: int = Field(description="课程周数")
    learning_objectives: List[str] = Field(description="总体学习目标")
    knowledge_points: List[KnowledgePoint] = Field(description="知识点列表")
    teaching_stages: List[TeachingStage] = Field(description="教学阶段")
    
    def get_stage_by_week(self, week: int) -> Optional[TeachingStage]:
        """根据周次获取教学阶段"""
        for stage in self.teaching_stages:
            if stage.week_start <= week <= stage.week_end:
                return stage
        return None
    
    def get_knowledge_point_by_id(self, kp_id: str) -> Optional[KnowledgePoint]:
        """根据ID获取知识点"""
        for kp in self.knowledge_points:
            if kp.id == kp_id:
                return kp
        return None

class SemesterSimulation(BaseModel):
    """学期模拟模型"""
    id: str
    course: Course
    current_week: int = Field(default=1, description="当前周次")
    current_stage: Optional[TeachingStage] = Field(default=None, description="当前教学阶段")
    students: List[Student] = Field(description="学生列表")
    assignments: List[Assignment] = Field(default_factory=list, description="作业列表")
    works: List[StudentWork] = Field(default_factory=list, description="学生作品")
    evaluations: List[PeerEvaluation] = Field(default_factory=list, description="互评记录")
    stage_history: List[Dict[str, Any]] = Field(default_factory=list, description="阶段历史记录")
    all_stage_reports: Dict[str, List[Dict[str, Any]]] = Field(default_factory=dict, description="各阶段学情报告集合")
    
    def get_kp_resolver(self):
        """获取知识点解析器
        
        Returns:
            KnowledgePointResolver: 基于当前课程的知识点解析器
        """
        from utils.knowledge_point_resolver import KnowledgePointResolver
        return KnowledgePointResolver(self.course)
    
    def resolve_kp_name(self, kp_id: str) -> str:
        """解析单个知识点名称
        
        Args:
            kp_id: 知识点ID
            
        Returns:
            知识点名称
        """
        resolver = self.get_kp_resolver()
        return resolver.get_name(kp_id)
    
    def resolve_kp_names(self, kp_ids: List[str]) -> List[str]:
        """解析多个知识点名称
        
        Args:
            kp_ids: 知识点ID列表
            
        Returns:
            知识点名称列表
        """
        resolver = self.get_kp_resolver()
        return resolver.get_names(kp_ids)
    
    def advance_to_next_stage(self) -> Optional[TeachingStage]:
        """进入下一个教学阶段"""
        if self.current_stage is None:
            # 开始第一个阶段
            self.current_stage = self.course.teaching_stages[0]
            self.current_week = self.current_stage.week_start
        else:
            # 找到下一个阶段
            current_index = -1
            for i, stage in enumerate(self.course.teaching_stages):
                if stage.stage_id == self.current_stage.stage_id:
                    current_index = i
                    break
            
            if current_index < len(self.course.teaching_stages) - 1:
                # 记录当前阶段历史
                self.stage_history.append({
                    "stage": self.current_stage.model_dump(),
                    "completed_week": self.current_week,
                    "completion_date": datetime.now().isoformat()
                })
                
                # 进入下一个阶段
                self.current_stage = self.course.teaching_stages[current_index + 1]
                self.current_week = self.current_stage.week_start
            else:
                # 课程结束
                return None
        
        return self.current_stage

def serialize_datetime(obj):
    """JSON序列化datetime对象的帮助函数"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    else:
        return obj

def safe_to_dict(model_instance):
    """安全地将Pydantic模型转换为可JSON序列化的字典"""
    data = model_instance.model_dump()
    return serialize_datetime(data)
