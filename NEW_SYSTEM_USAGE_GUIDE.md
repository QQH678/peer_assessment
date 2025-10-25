# 新记忆系统和教师分析功能使用指南

## 📅 创建日期
2025年10月20日

## 📚 概述

本指南介绍如何使用新一代学生记忆系统和增强的教师分析功能。

## 🎯 核心改进

### 1. 三维记忆结构
- ✅ **学习情况记忆** (LearningMemory): 记录作业完成、知识掌握
- ✅ **评价他人记忆** (PeerEvaluationMemory): 记录评价他人的过程和收获
- ✅ **被评价记忆** (ReceivedEvaluationMemory): 记录收到的反馈和改进
- ✅ **教师反馈记忆** (TeacherFeedbackMemory): 记录教师的分析和建议

### 2. 温度参数检索
- 基于知识蒸馏思想的优先级检索
- 自适应温度调整（掌握度高→低温度→精准检索）
- 越学越聪明的机制

### 3. 长短期记忆分离
- **短期记忆** (STM): 最近2-3轮，高访问优先级
- **长期记忆** (LTM): 重要经验，经过巩固的知识

### 4. 教师智能分析
- **每轮分析**: 知识状态、元认知、互评质量
- **阶段报告**: 综合学情报告，个性化建议

## 🚀 快速开始

### 步骤1: 创建新记忆系统

```python
from memory.new_memory_system import NewMemorySystem
from memory.new_memory_models import (
    LearningMemory, 
    PeerEvaluationMemory,
    ReceivedEvaluationMemory,
    MemoryDimension
)
from config.peer_review_config import PeerReviewConfig

# 创建配置
config = PeerReviewConfig.create_custom(
    rounds_per_stage=4,
    peers_per_round=3,
    base_temperature=1.0
)

# 创建记忆系统
memory_system = NewMemorySystem(
    student_id="student_001",
    use_semantic=True  # 启用语义检索
)
```

### 步骤2: 添加记忆

```python
# 学习记忆
learning_mem = LearningMemory(
    id="mem_learn_001",
    content="完成了二叉树遍历作业，掌握了递归思想",
    assignment_id="assign_001",
    assignment_title="二叉树遍历实现",
    knowledge_points=["二叉树", "递归", "DFS"],
    score=85,
    time_spent=3.5,
    importance=0.8,
    success_score=0.85,
    breakthroughs=["理解了递归的本质"],
    reflection="通过这次作业，我对递归有了更深的理解"
)
memory_system.add_memory(learning_mem)

# 评价他人记忆
peer_eval_mem = PeerEvaluationMemory(
    id="mem_eval_001",
    content="评价了张三的代码，学到了更简洁的写法",
    evaluated_student_id="student_002",
    evaluated_work_id="work_002",
    assignment_id="assign_001",
    evaluation_content="代码结构清晰，边界处理巧妙",
    evaluation_score=90,
    observed_strengths=["递归边界处理巧妙"],
    learning_from_peer=["学到了更简洁的边界条件"],
    self_reflection="看到他人的优秀实现让我意识到自己还有提升空间",
    importance=0.7
)
memory_system.add_memory(peer_eval_mem)

# 被评价记忆
received_mem = ReceivedEvaluationMemory(
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
    reflection_on_feedback="这个反馈很有帮助，我会在下次作业中改进",
    importance=0.8
)
memory_system.add_memory(received_mem)
```

### 步骤3: 检索记忆

```python
# 智能检索
result = memory_system.retrieve(
    query="如何处理递归的边界条件",
    dimension_filter=[MemoryDimension.LEARNING, MemoryDimension.PEER_EVALUATION],
    top_k=5
)

print(f"检索到 {len(result.retrieved_memories)} 条记忆")
print(f"使用温度: {result.temperature_used:.2f}")

for i, mem in enumerate(result.retrieved_memories):
    score = result.priority_scores[i]
    print(f"\n记忆 {i+1}:")
    print(f"  内容: {mem.content}")
    print(f"  维度: {mem.dimension}")
    print(f"  优先级: {score.total_priority:.3f}")
    print(f"  相关性: {score.relevance:.3f}")
    print(f"  时效性: {score.recency:.3f}")
    print(f"  重要性: {score.importance:.3f}")
```

### 步骤4: 推进轮次（触发记忆巩固）

```python
# 推进到下一轮
memory_system.advance_round()

# 查看统计
stats = memory_system.get_stats()
print(f"\n当前轮次: {stats['current_round']}")
print(f"短期记忆: {stats['stm_count']}")
print(f"长期记忆: {stats['ltm_count']}")
print(f"各维度分布: {stats['memories_by_dimension']}")
```

## 👨‍🏫 教师分析功能

### 创建教师分析器

```python
from agents.teachers.teacher_analyzer import TeacherAnalyzer

analyzer = TeacherAnalyzer()
```

### 每轮互评后分析

```python
# 分析学生表现
analysis_result = analyzer.analyze_after_round(
    student_id="student_001",
    round_id="round_001",
    student_work=student_work,  # StudentWork对象
    evaluations_given=[eval1, eval2],  # 学生给出的评价
    evaluations_received=[eval3, eval4],  # 学生收到的评价
    previous_knowledge_state={"二叉树": 0.6, "递归": 0.5}
)

# 查看分析结果
print("\n=== 知识状态分析 ===")
print(f"掌握度: {analysis_result.knowledge_state.knowledge_mastery}")
print(f"增长: {analysis_result.knowledge_state.knowledge_growth}")
print(f"强项: {analysis_result.knowledge_state.strengths}")
print(f"弱项: {analysis_result.knowledge_state.weaknesses}")

print("\n=== 元认知评估 ===")
print(f"总分: {analysis_result.metacognition.overall_score:.2f}")
print(f"自我认知: {analysis_result.metacognition.self_awareness:.2f}")
print(f"评价能力: {analysis_result.metacognition.evaluation_ability:.2f}")
print(f"反思质量: {analysis_result.metacognition.reflection_quality:.2f}")

print("\n=== 互评质量 ===")
print(f"总体质量: {analysis_result.evaluation_quality.overall_quality:.2f}")
print(f"深度: {analysis_result.evaluation_quality.depth:.2f}")
print(f"准确性: {analysis_result.evaluation_quality.accuracy:.2f}")
print(f"建设性: {analysis_result.evaluation_quality.constructiveness:.2f}")

print("\n=== 教师反馈 ===")
print(analysis_result.feedback_to_student)
print("\n行动建议:")
for item in analysis_result.action_items:
    print(f"  - {item}")
```

### 生成阶段学情报告

```python
# 阶段结束后生成报告
stage_report = analyzer.generate_stage_report(
    student_id="student_001",
    stage_id="stage_1",
    stage_name="基础算法阶段",
    start_round=1,
    end_round=4
)

print("\n=== 阶段学情报告 ===")
print(f"学生: {stage_report.student_id}")
print(f"阶段: {stage_report.stage_name}")
print(f"轮次范围: {stage_report.start_round}-{stage_report.end_round}")

print("\n知识掌握变化:")
print(f"  初始: {stage_report.initial_knowledge_mastery}")
print(f"  最终: {stage_report.final_knowledge_mastery}")

print(f"\n元认知增长: {stage_report.metacognition_growth:+.2f}")
print(f"互评质量提升: {stage_report.evaluation_quality_improvement:+.2f}")

print(f"\n总体表现: {stage_report.overall_performance}")
print("\n优势:")
for strength in stage_report.strengths:
    print(f"  ✓ {strength}")
print("\n不足:")
for weakness in stage_report.weaknesses:
    print(f"  ✗ {weakness}")

print("\n下阶段重点:")
for focus in stage_report.next_stage_focus:
    print(f"  → {focus}")

print(f"\n详细反馈:\n{stage_report.detailed_feedback}")
```

## ⚙️ 配置选项

### 互评轮次配置

```python
# 方式1: 使用配置类
from config.peer_review_config import PeerReviewConfig

config = PeerReviewConfig.create_custom(
    rounds_per_stage=5,  # 每阶段5轮互评
    peers_per_round=3,   # 每轮评价3个同伴
    reviews_per_work=3,  # 每份作业收到3个评价
    base_temperature=0.8,  # 较低温度，更聚焦
    stm_max_size=60,     # 短期记忆容量
    ltm_max_size=250     # 长期记忆容量
)

# 方式2: 环境变量（.env文件）
```env
ROUNDS_PER_STAGE=5
PEERS_PER_ROUND=3
REVIEWS_PER_WORK=3
MEMORY_BASE_TEMPERATURE=0.8
STM_MAX_SIZE=60
LTM_MAX_SIZE=250
```
```

### 记忆检索参数

```python
from memory.new_memory_models import MemoryRetrievalConfig

retrieval_config = MemoryRetrievalConfig(
    weight_relevance=0.4,    # 相关性权重
    weight_recency=0.2,      # 时效性权重
    weight_importance=0.3,   # 重要性权重
    weight_success=0.1,      # 成功度权重
    base_temperature=1.0,    # 基础温度
    temperature_adjustment=0.5,  # 温度调整系数
    recency_decay_rate=0.1,  # 时效衰减率
    top_k=5                  # 检索top-k
)
```

## 📊 完整流程示例

```python
from memory.new_memory_system import NewMemorySystem
from memory.new_memory_models import *
from agents.teachers.teacher_analyzer import TeacherAnalyzer
from config.peer_review_config import PeerReviewConfig

# 1. 初始化
config = PeerReviewConfig()
memory_system = NewMemorySystem("student_001")
analyzer = TeacherAnalyzer()

# 2. 模拟4轮互评
for round_num in range(1, 5):
    print(f"\n{'='*50}")
    print(f"第 {round_num} 轮互评")
    print('='*50)
    
    # 2.1 学生完成作业（添加学习记忆）
    learning_mem = LearningMemory(
        id=f"mem_learn_{round_num:03d}",
        content=f"第{round_num}轮作业完成",
        assignment_id=f"assign_{round_num:03d}",
        assignment_title=f"作业{round_num}",
        knowledge_points=["算法", "数据结构"],
        score=80 + round_num * 2,
        time_spent=3.0,
        importance=0.7,
        success_score=(80 + round_num * 2) / 100
    )
    memory_system.add_memory(learning_mem)
    
    # 2.2 评价他人（添加评价记忆）
    peer_mem = PeerEvaluationMemory(
        id=f"mem_eval_{round_num:03d}",
        content=f"第{round_num}轮评价他人",
        evaluated_student_id="student_002",
        evaluated_work_id=f"work_{round_num:03d}",
        assignment_id=f"assign_{round_num:03d}",
        evaluation_content="评价内容",
        evaluation_score=85,
        importance=0.6
    )
    memory_system.add_memory(peer_mem)
    
    # 2.3 收到评价（添加被评价记忆）
    received_mem = ReceivedEvaluationMemory(
        id=f"mem_received_{round_num:03d}",
        content=f"第{round_num}轮收到评价",
        evaluator_student_id="student_003",
        own_work_id=f"my_work_{round_num:03d}",
        assignment_id=f"assign_{round_num:03d}",
        received_evaluation="收到的评价",
        received_score=82,
        importance=0.7
    )
    memory_system.add_memory(received_mem)
    
    # 2.4 教师分析（模拟）
    # analysis = analyzer.analyze_after_round(...)
    
    # 2.5 推进轮次
    memory_system.advance_round()
    
    # 2.6 检索测试
    result = memory_system.retrieve("算法实现", top_k=3)
    print(f"检索到 {len(result.retrieved_memories)} 条记忆")
    print(f"温度: {result.temperature_used:.2f}")

# 3. 生成阶段报告
print(f"\n{'='*50}")
print("生成阶段报告")
print('='*50)

# stage_report = analyzer.generate_stage_report(
#     student_id="student_001",
#     stage_id="stage_1",
#     stage_name="算法基础",
#     start_round=1,
#     end_round=4
# )

# 4. 查看最终统计
stats = memory_system.get_stats()
print(f"\n最终统计:")
print(f"  总记忆数: {stats['total_memories']}")
print(f"  短期记忆: {stats['stm_count']}")
print(f"  长期记忆: {stats['ltm_count']}")
print(f"  各维度分布: {stats['memories_by_dimension']}")
```

## 🎓 高级用法

### 自定义记忆重要性

```python
# 标记突破性事件
breakthrough_mem = LearningMemory(
    id="mem_breakthrough",
    content="终于理解了动态规划的本质！",
    assignment_id="assign_dp",
    assignment_title="动态规划专题",
    knowledge_points=["动态规划", "最优子结构"],
    score=95,
    time_spent=5.0,
    importance=1.0,  # 最高重要性
    success_score=0.95,
    is_breakthrough=True,  # 标记为突破
    breakthroughs=["理解了状态转移方程的推导"]
)
```

### 维度过滤检索

```python
# 只检索学习记忆和教师反馈
result = memory_system.retrieve(
    query="如何提高代码质量",
    dimension_filter=[
        MemoryDimension.LEARNING,
        MemoryDimension.TEACHER_FEEDBACK
    ],
    top_k=5
)
```

### 手动更新知识掌握度

```python
# 影响检索温度
memory_system.update_knowledge_mastery("二叉树", 0.9)  # 高掌握度
memory_system.update_knowledge_mastery("图论", 0.3)    # 低掌握度

# 高掌握度知识点 → 低温度 → 精准检索
# 低掌握度知识点 → 高温度 → 探索性检索
```

## 📈 优势总结

1. **更智能的记忆**: 三维结构全面捕捉学习过程
2. **自适应检索**: 温度参数让记忆检索越来越精准
3. **教师洞察**: 深度分析学生的知识和能力发展
4. **个性化指导**: 基于数据的针对性建议
5. **可配置性**: 灵活适应不同教学场景

## 🔧 故障排除

### Q: 语义检索不可用？
A: 安装依赖：`pip install sentence-transformers faiss-cpu`

### Q: 记忆检索结果不理想？
A: 调整权重配置，增加相关性权重或降低温度参数

### Q: 教师分析API调用失败？
A: 检查OpenAI API配置，确保有足够的quota

## 📝 下一步

- [ ] 集成到学生Agent
- [ ] 集成到模拟器
- [ ] 完善教师Agent
- [ ] 编写集成测试
- [ ] 优化性能

---

**文档版本**: v1.0  
**最后更新**: 2025-10-20  
**作者**: GitHub Copilot
