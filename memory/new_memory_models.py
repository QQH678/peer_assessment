"""
新一代学生记忆系统 - 数据模型
基于三维记忆结构和温度优先级检索
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Tuple, Literal
from datetime import datetime
from enum import Enum
import math


class MemoryDimension(str, Enum):
    """记忆维度枚举"""
    LEARNING = "learning"  # 学习情况记忆
    PEER_EVALUATION = "peer_evaluation"  # 评价他人记忆
    RECEIVED_EVALUATION = "received_evaluation"  # 被评价记忆
    TEACHER_FEEDBACK = "teacher_feedback"  # 教师反馈记忆


class MemoryType(str, Enum):
    """记忆类型：短期/长期"""
    SHORT_TERM = "short_term"  # STM
    LONG_TERM = "long_term"  # LTM


class MemoryItem(BaseModel):
    """记忆项基类"""
    id: str = Field(description="记忆唯一标识")
    dimension: MemoryDimension = Field(description="记忆维度")
    memory_type: MemoryType = Field(default=MemoryType.SHORT_TERM, description="记忆类型")
    
    timestamp: datetime = Field(default_factory=datetime.now, description="创建时间")
    
    # 内容
    content: str = Field(description="记忆内容描述")
    # 注意: structured_data 已删除（始终为空字典，无实际用途）
    
    # 优先级相关因子
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性[0-1]")
    success_score: float = Field(default=0.5, ge=0.0, le=1.0, description="成功度[0-1]")
    access_count: int = Field(default=0, description="访问次数")
    last_accessed: Optional[datetime] = Field(default=None, description="最后访问时间")
    
    # 注意: 以下字段已删除以减少存储空间和提高可读性
    # - embedding: 运行时动态计算，不需要持久化（占用17%文件空间）
    # - related_knowledge_points: 功能未实现，始终为空
    # - related_memory_ids: 功能未实现，始终为空
    
    # 标记
    is_breakthrough: bool = Field(default=False, description="是否突破性事件")
    is_consolidated: bool = Field(default=False, description="是否已巩固到LTM")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class LearningMemory(MemoryItem):
    """学习情况记忆"""
    dimension: Literal[MemoryDimension.LEARNING] = MemoryDimension.LEARNING
    
    assignment_id: str = Field(description="作业ID")
    assignment_title: str = Field(description="作业标题")
    knowledge_points: List[str] = Field(description="涉及知识点")
    
    score: float = Field(description="得分")
    time_spent: float = Field(description="耗时(小时)")
    
    difficulties_encountered: List[str] = Field(default_factory=list, description="遇到的困难")
    breakthroughs: List[str] = Field(default_factory=list, description="突破点")
    learning_strategies: List[str] = Field(default_factory=list, description="使用的学习策略")
    
    reflection: str = Field(default="", description="学习反思")


class PeerEvaluationMemory(MemoryItem):
    """评价他人记忆"""
    dimension: Literal[MemoryDimension.PEER_EVALUATION] = MemoryDimension.PEER_EVALUATION
    
    evaluated_student_id: str = Field(description="被评价学生ID")
    evaluated_work_id: str = Field(description="被评价作业ID")
    assignment_id: str = Field(description="作业ID")
    
    evaluation_content: str = Field(description="评价内容")
    evaluation_score: float = Field(description="给出的分数")
    
    # 评价过程中的思考
    observed_strengths: List[str] = Field(default_factory=list, description="发现的优点")
    observed_weaknesses: List[str] = Field(default_factory=list, description="发现的问题")
    learning_from_peer: List[str] = Field(default_factory=list, description="从同伴学到的")
    
    self_reflection: str = Field(default="", description="评价他人时的自我反思")
    
    # 元认知
    evaluation_quality: Optional[float] = Field(default=None, description="评价质量(由教师评估)")


class ReceivedEvaluationMemory(MemoryItem):
    """被评价记忆"""
    dimension: Literal[MemoryDimension.RECEIVED_EVALUATION] = MemoryDimension.RECEIVED_EVALUATION
    
    evaluator_student_id: str = Field(description="评价者ID")
    own_work_id: str = Field(description="自己的作业ID")
    assignment_id: str = Field(description="作业ID")
    
    received_evaluation: str = Field(description="收到的评价内容")
    received_score: float = Field(description="收到的分数")
    
    # 对评价的反应
    agreement_level: float = Field(default=0.5, ge=0.0, le=1.0, description="认同程度[0-1]")
    insights_gained: List[str] = Field(default_factory=list, description="获得的洞察")
    improvement_actions: List[str] = Field(default_factory=list, description="改进行动")
    
    reflection_on_feedback: str = Field(default="", description="对反馈的反思")
    
    # 改进效果
    improvement_verified: bool = Field(default=False, description="改进是否得到验证")
    improvement_score: Optional[float] = Field(default=None, description="改进效果得分")


class TeacherFeedbackMemory(MemoryItem):
    """教师反馈记忆"""
    dimension: Literal[MemoryDimension.TEACHER_FEEDBACK] = MemoryDimension.TEACHER_FEEDBACK
    
    round_id: str = Field(description="互评轮次ID")
    stage_id: Optional[str] = Field(default=None, description="教学阶段ID")
    
    # 知识状态分析
    knowledge_state: Dict[str, float] = Field(description="知识点掌握度")
    knowledge_growth: Dict[str, float] = Field(default_factory=dict, description="知识点增长")
    
    # 元认知评估
    metacognition_level: float = Field(description="元认知水平[0-1]")
    
    # 互评质量评估
    evaluation_quality: Dict[str, float] = Field(description="评价质量（深度、准确性、建设性）")
    
    # 教师反馈内容
    feedback_content: str = Field(description="教师反馈")
    strengths: List[str] = Field(default_factory=list, description="优势")
    weaknesses: List[str] = Field(default_factory=list, description="不足")
    recommendations: List[str] = Field(default_factory=list, description="建议")
    
    # 学情报告（阶段性）
    is_stage_report: bool = Field(default=False, description="是否为阶段报告")
    stage_summary: Optional[str] = Field(default=None, description="阶段总结")


class MemoryPriorityScore(BaseModel):
    """记忆优先级分数"""
    memory_id: str
    
    # 各因子得分
    relevance: float = Field(ge=0.0, le=1.0, description="相关性")
    recency: float = Field(ge=0.0, le=1.0, description="时效性")
    importance: float = Field(ge=0.0, le=1.0, description="重要性")
    success: float = Field(ge=0.0, le=1.0, description="成功度")
    
    # 综合优先级
    total_priority: float = Field(description="综合优先级分数")
    
    # 温度调整后的概率
    retrieval_probability: float = Field(description="检索概率")


class MemoryRetrievalConfig(BaseModel):
    """记忆检索配置"""
    # 优先级权重
    weight_relevance: float = Field(default=0.4, description="相关性权重")
    weight_recency: float = Field(default=0.2, description="时效性权重")
    weight_importance: float = Field(default=0.3, description="重要性权重")
    weight_success: float = Field(default=0.1, description="成功度权重")
    
    # 温度参数
    base_temperature: float = Field(default=1.0, ge=0.1, le=2.0, description="基础温度")
    temperature_adjustment: float = Field(default=0.5, description="温度调整系数")
    
    # 时效性衰减
    recency_decay_rate: float = Field(default=0.1, description="时效性衰减率λ")
    
    # 检索数量
    top_k: int = Field(default=5, description="检索top-k记忆")
    
    # 维度权重（可选，控制不同维度的检索倾向）
    dimension_weights: Dict[MemoryDimension, float] = Field(
        default_factory=lambda: {
            MemoryDimension.LEARNING: 1.0,
            MemoryDimension.PEER_EVALUATION: 0.8,
            MemoryDimension.RECEIVED_EVALUATION: 0.9,
            MemoryDimension.TEACHER_FEEDBACK: 1.0
        }
    )


class MemoryConsolidationRule(BaseModel):
    """记忆巩固规则"""
    # 时间条件
    min_age_rounds: int = Field(default=6, description="最小年龄(轮次)")
    
    # 重要性阈值
    importance_threshold: float = Field(default=0.7, description="重要性阈值")
    
    # 访问条件
    min_access_count: int = Field(default=3, description="最小访问次数")
    
    # 突破性事件直接巩固
    auto_consolidate_breakthrough: bool = Field(default=True)


class StudentMemoryState(BaseModel):
    """学生记忆状态"""
    student_id: str
    
    # 短期记忆
    short_term_memories: List[MemoryItem] = Field(default_factory=list)
    
    # 长期记忆
    long_term_memories: List[MemoryItem] = Field(default_factory=list)
    
    # 统计信息
    total_memories: int = Field(default=0)
    memories_by_dimension: Dict[MemoryDimension, int] = Field(default_factory=dict)
    
    # 知识掌握度
    knowledge_mastery: Dict[str, float] = Field(default_factory=dict)
    
    # 元认知水平追踪
    metacognition_history: List[Tuple[datetime, float]] = Field(default_factory=list)
    
    # 当前检索配置
    retrieval_config: MemoryRetrievalConfig = Field(default_factory=MemoryRetrievalConfig)
    
    # 巩固规则
    consolidation_rule: MemoryConsolidationRule = Field(default_factory=MemoryConsolidationRule)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class MemoryRetrievalResult(BaseModel):
    """记忆检索结果"""
    query: str = Field(description="查询内容")
    retrieved_memories: List[MemoryItem] = Field(description="检索到的记忆")
    priority_scores: List[MemoryPriorityScore] = Field(description="优先级分数")
    
    temperature_used: float = Field(description="使用的温度参数")
    total_candidates: int = Field(description="候选记忆总数")
    
    # 统计
    dimensions_retrieved: Dict[MemoryDimension, int] = Field(
        default_factory=dict, 
        description="各维度检索数量"
    )


def compute_recency_score(timestamp: datetime, decay_rate: float = 0.1) -> float:
    """
    计算时效性得分
    
    Args:
        timestamp: 记忆时间戳
        decay_rate: 衰减率λ
    
    Returns:
        时效性得分 [0, 1]
    """
    days_passed = (datetime.now() - timestamp).days
    return math.exp(-decay_rate * days_passed)


def compute_memory_priority(
    memory: MemoryItem,
    relevance: float,
    config: MemoryRetrievalConfig
) -> MemoryPriorityScore:
    """
    计算记忆优先级分数
    
    Args:
        memory: 记忆项
        relevance: 相关性得分（由语义相似度计算）
        config: 检索配置
    
    Returns:
        优先级分数对象
    """
    # 计算时效性
    recency = compute_recency_score(memory.timestamp, config.recency_decay_rate)
    
    # 获取重要性和成功度
    importance = memory.importance
    success = memory.success_score
    
    # 计算综合优先级
    total_priority = (
        config.weight_relevance * relevance +
        config.weight_recency * recency +
        config.weight_importance * importance +
        config.weight_success * success
    )
    
    return MemoryPriorityScore(
        memory_id=memory.id,
        relevance=relevance,
        recency=recency,
        importance=importance,
        success=success,
        total_priority=total_priority,
        retrieval_probability=0.0  # 将在温度调整后计算
    )


def softmax_with_temperature(scores: List[float], temperature: float) -> List[float]:
    """
    带温度参数的softmax
    
    Args:
        scores: 分数列表
        temperature: 温度参数
    
    Returns:
        概率分布
    """
    import numpy as np
    
    # 温度调整
    adjusted_scores = np.array(scores) / temperature
    
    # softmax
    exp_scores = np.exp(adjusted_scores - np.max(adjusted_scores))  # 数值稳定
    probabilities = exp_scores / np.sum(exp_scores)
    
    return probabilities.tolist()


def compute_adaptive_temperature(
    base_temperature: float,
    mastery_level: float,
    adjustment_factor: float = 0.5
) -> float:
    """
    计算自适应温度参数
    
    Args:
        base_temperature: 基础温度
        mastery_level: 知识掌握度 [0, 1]
        adjustment_factor: 调整系数
    
    Returns:
        调整后的温度
    """
    # 掌握度高 -> 温度低（聚焦）
    # 掌握度低 -> 温度高（探索）
    temperature = base_temperature + adjustment_factor * (1 - mastery_level)
    return max(0.1, min(2.0, temperature))  # 限制范围


if __name__ == "__main__":
    # 示例：创建各类记忆
    
    # 1. 学习记忆
    learning_mem = LearningMemory(
        id="mem_learn_001",
        content="完成了二叉树遍历作业，掌握了递归思想",
        structured_data={
            "assignment_id": "assign_001",
            "score": 85
        },
        assignment_id="assign_001",
        assignment_title="二叉树遍历实现",
        knowledge_points=["二叉树", "递归", "DFS"],
        score=85,
        time_spent=3.5,
        importance=0.8,
        success_score=0.85
    )
    
    # 2. 评价他人记忆
    peer_eval_mem = PeerEvaluationMemory(
        id="mem_eval_001",
        content="评价了张三的代码，发现他的递归边界处理很巧妙",
        evaluated_student_id="student_002",
        evaluated_work_id="work_002",
        assignment_id="assign_001",
        evaluation_content="代码结构清晰，边界处理得当",
        evaluation_score=90,
        observed_strengths=["递归边界处理巧妙", "代码可读性强"],
        learning_from_peer=["学到了更简洁的边界条件写法"],
        importance=0.7
    )
    
    # 3. 被评价记忆
    received_eval_mem = ReceivedEvaluationMemory(
        id="mem_received_001",
        content="李四指出我的代码缺少边界检查",
        evaluator_student_id="student_003",
        own_work_id="work_001",
        assignment_id="assign_001",
        received_evaluation="代码逻辑正确，但缺少输入验证",
        received_score=80,
        agreement_level=0.9,
        insights_gained=["需要加强输入验证意识"],
        improvement_actions=["在下次作业中加入完善的输入检查"],
        importance=0.8
    )
    
    # 4. 教师反馈记忆
    teacher_feedback_mem = TeacherFeedbackMemory(
        id="mem_teacher_001",
        content="第一轮互评后的反馈",
        round_id="round_001",
        knowledge_state={"二叉树": 0.75, "递归": 0.80},
        metacognition_level=0.65,
        evaluation_quality={"depth": 0.7, "accuracy": 0.8, "constructiveness": 0.75},
        feedback_content="整体表现良好，评价他人时能够抓住重点",
        strengths=["代码实现能力强", "评价有一定深度"],
        weaknesses=["对算法复杂度分析不够"],
        recommendations=["加强时间复杂度分析的学习"],
        importance=0.9
    )
    
    print("✅ 新记忆数据模型创建成功！")
    print(f"学习记忆: {learning_mem.id}")
    print(f"评价记忆: {peer_eval_mem.id}")
    print(f"被评价记忆: {received_eval_mem.id}")
    print(f"教师反馈: {teacher_feedback_mem.id}")
