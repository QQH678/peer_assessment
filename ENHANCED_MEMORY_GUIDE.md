# 增强版记忆系统使用指南

## 📋 概述

增强版记忆系统在原有基础上增加了两个核心优化：

1. **语义向量检索** - 使用预训练语言模型实现真正的语义理解
2. **自适应学习路径** - 基于概念掌握度生成个性化学习计划

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 基础依赖（必需）
pip install openai pydantic python-dotenv faker tqdm numpy

# 语义检索依赖（推荐）
pip install sentence-transformers faiss-cpu torch

# 如果有GPU，可以安装GPU版本以获得更好的性能
pip install faiss-gpu
```

### 2. 基本使用

```python
from memory.enhanced_memory import create_enhanced_memory_system
from memory.intelligent_memory import MemoryContext, LearningOutcome

# 创建记忆系统
memory_system = create_enhanced_memory_system(
    student_id="student_001",
    config={
        "use_semantic_retrieval": True,  # 启用语义检索
        "semantic_model": "paraphrase-multilingual-MiniLM-L12-v2",  # 支持中文
        "use_faiss": True,  # 使用FAISS加速
        "use_gpu": False    # 是否使用GPU
    }
)

# 存储学习经验
context = MemoryContext(
    knowledge_point_ids=["链表", "数组", "动态内存"],
    difficulty_level=3,
    current_problem="实现图书管理系统",
    available_resources=["教材", "网络"],
    time_constraints=120,
    learning_objectives=["掌握链表操作", "理解动态内存分配"]
)

outcome = LearningOutcome(
    success=True,
    score=85.0,
    concepts_learned=["链表", "动态内存"],
    concepts_reinforced=["数组"],
    errors_made=["内存泄漏"],
    time_spent=100,
    reflection="很好的学习经历，对链表有了更深的理解"
)

memory_system.store_learning_experience(
    problem="实现一个图书管理系统，支持增删改查和借阅管理",
    solution="使用动态数组存储图书信息...",
    context=context,
    outcome=outcome
)

# 检索相关案例
result = memory_system.retrieve_relevant_cases(
    current_problem="设计学生管理系统",
    context=context,
    max_cases=5
)

print(f"检索到 {len(result.retrieved_cases)} 个案例")
print(f"置信度: {result.confidence_level:.2%}")
print(f"说明: {result.explanation}")

for case, score in zip(result.retrieved_cases, result.similarity_scores):
    print(f"[{score:.3f}] {case.get('problem_description', '')[:50]}...")
```

---

## 🎯 核心功能

### 1. 语义向量检索

#### 特性
- ✅ 真正的语义理解，不仅仅是关键词匹配
- ✅ 支持中英文混合查询
- ✅ 自动相似度计算和排序
- ✅ 结合上下文（知识点、难度）进行重排序
- ✅ 置信度评估和解释生成

#### 推荐模型

| 模型名称 | 维度 | 语言支持 | 速度 | 效果 |
|---------|------|---------|------|-----|
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 | 多语言(含中文) | 快 | 好 ⭐推荐 |
| `paraphrase-multilingual-mpnet-base-v2` | 768 | 多语言(含中文) | 中 | 很好 |
| `distiluse-base-multilingual-cased-v2` | 512 | 多语言 | 快 | 中等 |

#### 示例：自定义模型

```python
memory_system = create_enhanced_memory_system(
    student_id="student_001",
    config={
        "semantic_model": "paraphrase-multilingual-mpnet-base-v2",  # 更大的模型
        "use_faiss": True,
        "use_gpu": True  # 启用GPU加速
    }
)
```

#### 检索结果说明

```python
result = memory_system.retrieve_relevant_cases(...)

# result包含以下字段：
# - retrieved_cases: 检索到的案例列表（字典）
# - similarity_scores: 每个案例的相似度分数 (0-1)
# - confidence_level: 整体置信度 (0-1)
# - explanation: 可读的结果说明
# - retrieval_time_ms: 检索耗时（毫秒）
```

#### 相似度分数解释

- **> 0.8**: 高度相关，可以直接参考
- **0.6 - 0.8**: 较为相关，需要结合具体情况调整
- **0.4 - 0.6**: 一般相关，主要提供思路
- **< 0.4**: 相关性较低，仅作参考

---

### 2. 自适应学习路径

#### 特性
- ✅ 基于概念掌握度分析学习状态
- ✅ 自动识别薄弱知识点
- ✅ 考虑前置依赖关系
- ✅ 生成个性化学习目标
- ✅ 推荐下一步学习内容
- ✅ 估算学习时间和成功概率

#### 生成学习路径

```python
# 生成学习路径
learning_path = memory_system.generate_learning_path(
    time_budget=30,      # 时间预算（天）
    daily_study_time=120 # 每日学习时间（分钟）
)

if learning_path:
    print(f"当前阶段: {learning_path.current_stage}")  # novice/beginner/intermediate/advanced/expert
    print(f"预计完成时间: {learning_path.estimated_completion_time} 天")
    print(f"成功概率: {learning_path.success_probability:.2%}")
    
    # 查看学习目标
    for goal in learning_path.goals:
        print(f"\n目标: {goal.concept}")
        print(f"  当前掌握: {goal.current_mastery:.2%}")
        print(f"  目标掌握: {goal.target_mastery:.2%}")
        print(f"  优先级: {goal.priority}")  # high/medium/low
        print(f"  预计时间: {goal.estimated_time} 分钟")
        print(f"  推荐行动:")
        for action in goal.recommended_actions:
            print(f"    • {action}")
    
    # 查看推荐的下一个作业
    next_assignment = learning_path.next_assignment_recommendation
    print(f"\n推荐下一个作业:")
    print(f"  类型: {next_assignment['type']}")
    print(f"  难度: {next_assignment['difficulty']}")
    print(f"  重点概念: {next_assignment['focus']}")
    print(f"  描述: {next_assignment['description']}")
```

#### 概念掌握度分析

```python
# 分析概念掌握情况
analysis = memory_system.analyze_concept_mastery()

print(f"总体掌握度: {analysis['overall_mastery']:.2%}")
print(f"学习阶段: {analysis['learning_stage']}")
print(f"已掌握概念: {len(analysis['mastered_concepts'])} 个")
print(f"薄弱概念: {len(analysis['weak_concepts'])} 个")

# 查看分布
for level, count in analysis['mastery_distribution'].items():
    print(f"  {level}: {count} 个概念")

# 薄弱概念详情
if analysis['weak_concepts']:
    print("\n薄弱概念（需要重点加强）:")
    for concept in analysis['weak_concepts']:
        mastery = memory_system.memory_state.concept_mastery.get(concept, 0)
        print(f"  • {concept}: {mastery:.2%}")
```

#### 获取学习建议

```python
# 获取针对当前学习内容的建议
recommendations = memory_system.get_learning_recommendations(context)

for rec in recommendations:
    if rec['type'] == 'priority_concept':
        print(f"\n优先学习: {rec['concept']}")
        print(f"原因: {rec['reason']}")
        print(f"当前掌握: {rec['current_mastery']:.2%}")
        
        # 推荐的学习资源
        for resource in rec['recommended_resources']:
            print(f"  • [{resource['type']}] {resource['title']}")
            print(f"    难度: {resource['difficulty']}, 预计: {resource['estimated_time']}分钟")
```

---

## 📊 系统统计

```python
# 获取系统统计信息
stats = memory_system.get_system_statistics()

print(f"学生ID: {stats['student_id']}")
print(f"总案例数: {stats['total_cases']}")
print(f"总检索次数: {stats['total_retrievals']}")
print(f"记忆有效性: {stats['memory_effectiveness']:.2%}")

# 语义检索统计
if 'semantic_retrieval' in stats:
    sr = stats['semantic_retrieval']
    print(f"\n语义检索:")
    print(f"  索引大小: {sr['index_size']}")
    print(f"  索引类型: {sr['index_type']}")
    print(f"  缓存命中率: {sr['cache_hit_rate']:.2%}")
    print(f"  平均检索时间: {sr['average_retrieval_time']*1000:.2f}ms")

# 概念掌握分析
if 'mastery_analysis' in stats:
    ma = stats['mastery_analysis']
    print(f"\n概念掌握:")
    print(f"  学习阶段: {ma['learning_stage']}")
    print(f"  总体掌握度: {ma['overall_mastery']:.2%}")
```

---

## 🔧 高级配置

### 配置选项

```python
config = {
    # 语义检索配置
    "use_semantic_retrieval": True,  # 是否启用语义检索
    "semantic_model": "paraphrase-multilingual-MiniLM-L12-v2",  # 模型名称
    "use_faiss": None,  # None表示自动判断，True强制使用FAISS
    "use_gpu": False,   # 是否使用GPU
    
    # 记忆系统配置（继承自基础系统）
    "vector_dimension": 100,
    "similarity_threshold": 0.5,
    "max_cases_stored": 1000,
    "replay_sample_size": 5
}

memory_system = create_enhanced_memory_system(
    student_id="student_001",
    config=config
)
```

### 性能优化

#### 1. 使用FAISS加速（大规模数据）

```python
# 当案例数超过100个时，FAISS可以显著提升检索速度
config = {
    "use_faiss": True,
    "use_gpu": False  # 如果有GPU，设为True可进一步加速
}
```

#### 2. 批量添加案例

```python
# 批量添加比逐个添加更高效
cases_to_add = [
    (case_id_1, case_data_1),
    (case_id_2, case_data_2),
    # ...
]

if memory_system.semantic_engine:
    memory_system.semantic_engine.add_cases_batch(cases_to_add)
```

#### 3. 启用缓存

```python
# 检索时使用缓存（默认启用）
result = memory_system.retrieve_relevant_cases(
    current_problem=query,
    context=context,
    max_cases=5
)
# 相同查询会直接从缓存返回结果
```

---

## 🎨 应用场景

### 场景1：智能作业推荐

```python
# 根据学生当前学习状态推荐合适的作业
learning_path = memory_system.generate_learning_path(time_budget=7)

next_assignment = learning_path.next_assignment_recommendation

# 使用推荐信息生成作业
assignment = Assignment(
    title=f"针对{next_assignment['focus']}的练习",
    description=next_assignment['description'],
    difficulty_level=next_assignment['difficulty'],
    knowledge_points_covered=next_assignment['target_concepts'],
    estimated_hours=next_assignment['estimated_time'] // 60
)
```

### 场景2：相似问题推荐

```python
# 学生遇到困难时，推荐相似的已解决问题
context = MemoryContext(
    knowledge_point_ids=current_assignment.knowledge_points_covered,
    difficulty_level=current_assignment.difficulty_level,
    current_problem=current_assignment.description,
    available_resources=[],
    time_constraints=120,
    learning_objectives=[]
)

result = memory_system.retrieve_relevant_cases(
    current_problem=current_assignment.description,
    context=context,
    max_cases=3
)

if result.confidence_level > 0.6:
    print("找到相似案例，可以参考：")
    for case in result.retrieved_cases:
        print(f"- {case.get('problem_description')}")
        print(f"  解决方案: {case.get('solution')[:100]}...")
```

### 场景3：学习进度监控

```python
# 定期分析学习进度
analysis = memory_system.analyze_concept_mastery()

if analysis['overall_mastery'] < 0.5:
    print("⚠️  学习进度较慢，需要加强基础")
    weak_concepts = analysis['weak_concepts'][:3]
    print(f"建议重点学习: {', '.join(weak_concepts)}")
elif analysis['overall_mastery'] > 0.8:
    print("🎉 学习进度很好，可以尝试更有挑战的内容")
```

---

## 🐛 故障排除

### 问题1：无法使用语义检索

**症状**: 提示 "sentence-transformers not available"

**解决**:
```bash
pip install sentence-transformers torch
```

### 问题2：检索速度慢

**原因**: 案例数量较多且未使用FAISS

**解决**:
```bash
pip install faiss-cpu  # 或 faiss-gpu
```

然后设置配置：
```python
config = {"use_faiss": True}
```

### 问题3：内存占用高

**原因**: 语义模型较大

**解决**: 使用更小的模型
```python
config = {
    "semantic_model": "paraphrase-multilingual-MiniLM-L12-v2"  # 最小模型
}
```

### 问题4：首次加载慢

**原因**: 需要下载预训练模型

**解决**: 首次使用时会自动下载，之后会使用缓存。可以预先下载：
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
# 模型会下载到 ~/.cache/torch/sentence_transformers/
```

---

## 📈 性能对比

### TF-IDF vs 语义检索

| 维度 | TF-IDF | 语义检索 |
|-----|--------|---------|
| 语义理解 | ❌ 无 | ✅ 强 |
| 中文支持 | ⚠️  一般 | ✅ 好 |
| 速度 | ✅ 快 | ⚠️  中等 |
| 准确性 | ⚠️  中等 | ✅ 高 |
| 内存占用 | ✅ 低 | ⚠️  中等 |

### 建议
- 案例数 < 50：TF-IDF即可
- 案例数 50-500：语义检索 + Numpy索引
- 案例数 > 500：语义检索 + FAISS索引
- 有GPU：语义检索 + FAISS-GPU

---

## 📝 最佳实践

1. **及时存储学习经验**: 每完成一个作业就存储，保持记忆系统更新

2. **提供详细的反思**: `reflection`字段对后续学习很有帮助

3. **准确标记概念**: `concepts_learned`和`concepts_reinforced`要准确

4. **定期分析**: 每周分析一次概念掌握情况

5. **渐进式学习**: 按照推荐的学习路径，不要跳过前置知识

6. **多样化练习**: 不同类型的练习有助于全面掌握

---

## 🔗 相关资源

- [sentence-transformers文档](https://www.sbert.net/)
- [FAISS文档](https://github.com/facebookresearch/faiss)
- [预训练模型列表](https://www.sbert.net/docs/pretrained_models.html)

---

## 💡 示例代码

完整的示例代码请参考：
- `test_enhanced_memory.py` - 功能测试
- `optimization/adaptive_learning.py` - 自适应学习示例
- `memory/semantic_retrieval.py` - 语义检索示例

---

**更新时间**: 2025-10-05  
**版本**: v2.0  
**作者**: System Optimizer
