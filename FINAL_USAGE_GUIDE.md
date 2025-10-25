# 🎉 新记忆系统 - 最终使用指南

## 恭喜！系统已完全就绪 ✅

新开发的**三维记忆系统**和**教师智能分析**已经完全集成到现有的学期模拟中。

---

## 🚀 立即开始使用

### 方式1: 学期模拟 + 新记忆系统（推荐）

```bash
# 最简单的用法
python main.py --experiment semester --use-new-memory

# 完整参数示例
python main.py --experiment semester \
    --course-name "数据结构与算法" \
    --subject "计算机科学" \
    --student-count 30 \
    --duration-weeks 16 \
    --evaluations-per-work 4 \
    --rounds-per-stage 3 \
    --peers-per-round 2 \
    --memory-temperature 1.0 \
    --use-new-memory
```

### 方式2: 纯新记忆系统实验

```bash
python main.py --mode new_memory \
    --use-new-memory \
    --enable-teacher-analysis
```

### 方式3: 运行测试验证

```bash
# 完整集成测试
python test_integration_complete.py

# 简单集成测试
python test_simple_integration.py
```

---

## 📋 可用参数列表

| 参数 | 说明 | 默认值 |
|-----|------|--------|
| `--experiment semester` | 使用学期模拟模式 | 必需 |
| `--use-new-memory` | 启用新三维记忆系统 | False |
| `--course-name` | 课程名称 | "Python程序设计" |
| `--subject` | 学科领域 | "计算机科学" |
| `--student-count` | 学生数量 | 25 |
| `--duration-weeks` | 课程周数 | 16 |
| `--evaluations-per-work` | 每作品被评价次数 | 3 |
| `--rounds-per-stage` | 每阶段互评轮次 | 3 |
| `--peers-per-round` | 每轮评价同伴数 | 2 |
| `--memory-temperature` | 记忆检索温度 | 1.0 |

---

## 💡 使用场景

### 场景1: 小规模快速测试
```bash
python main.py --experiment semester \
    --student-count 5 \
    --duration-weeks 4 \
    --rounds-per-stage 2 \
    --use-new-memory
```

### 场景2: 标准教学实验
```bash
python main.py --experiment semester \
    --course-name "数据结构" \
    --student-count 30 \
    --duration-weeks 16 \
    --use-new-memory
```

### 场景3: 高级研究实验
```bash
python main.py --experiment semester \
    --course-name "机器学习" \
    --subject "人工智能" \
    --student-count 50 \
    --duration-weeks 18 \
    --rounds-per-stage 4 \
    --memory-temperature 0.8 \
    --use-new-memory
```

---

## 🎯 核心功能

### 1. 三维记忆系统
- **学习记忆**: 记录作业完成、知识掌握情况
- **评价记忆**: 记录评价他人的经验和标准
- **被评价记忆**: 记录收到的反馈和改进方向
- **教师反馈**: 记录教师的指导和建议

### 2. 温度参数检索
- 优先级 = 0.4×相关性 + 0.2×时新性 + 0.3×重要性 + 0.1×成功度
- Softmax温度调控，平衡探索与利用
- 自适应温度调整

### 3. 长短期记忆
- 短期记忆(STM): 最大50条
- 长期记忆(LTM): 最大200条
- 访问次数≥3自动巩固到LTM

### 4. 教师智能分析
- 知识状态分析
- 元认知评估
- 互评质量评估
- 阶段学情报告

---

## 📊 预期输出

运行后会在`data/semester_*/`目录生成：

```
data/semester_xxxx/
├── course.json           # 课程设计
├── students.json         # 学生信息（含记忆状态）
├── assignments.json      # 作业列表
├── works.json           # 学生作品
├── evaluations.json     # 互评记录
└── statistics.json      # 统计分析
```

---

## 🔍 查看结果

### 1. 学生记忆状态
```python
# 在students.json中查看
{
  "student_id": "xxx",
  "short_term_memory": {...},  # 短期记忆
  "long_term_memory": {...},   # 长期记忆
  "knowledge_mastery": {...}   # 知识掌握度
}
```

### 2. 教师分析报告
日志中会输出每轮的分析结果：
- 知识状态分析
- 元认知评估
- 互评质量评估

---

## ⚙️ 配置调优

### 调整记忆温度
```bash
# 更聚焦（选择高优先级记忆）
--memory-temperature 0.5

# 平衡（默认）
--memory-temperature 1.0

# 更多样（增加探索性）
--memory-temperature 1.5
```

### 调整互评轮次
```bash
# 少量互评（快速测试）
--rounds-per-stage 2

# 适中互评（标准实验）
--rounds-per-stage 3

# 大量互评（深度研究）
--rounds-per-stage 5
```

---

## 📚 相关文档

- **QUICKSTART.md** - 快速启动指南
- **SEMESTER_INTEGRATION_SUMMARY.md** - 学期模拟集成总结
- **FINAL_INTEGRATION_SUMMARY.md** - 完整集成总结
- **NEW_MEMORY_DESIGN.md** - 系统架构设计
- **INTEGRATION_TEST_REPORT.md** - 测试报告

---

## ✅ 验证清单

在开始实验前，请确认：

- [ ] 已安装所有依赖：`pip install -r requirements.txt`
- [ ] API配置正确（在`.env`或`config/settings.py`）
- [ ] 有足够的磁盘空间存储结果
- [ ] （可选）有GPU可以加速语义检索

---

## 🎓 最佳实践

1. **首次使用**：先用小规模参数测试
   ```bash
   python main.py --experiment semester \
       --student-count 5 --duration-weeks 4 --use-new-memory
   ```

2. **正式实验**：使用标准参数
   ```bash
   python main.py --experiment semester \
       --student-count 30 --use-new-memory
   ```

3. **查看结果**：检查`data/semester_*/`目录

4. **分析数据**：使用分析工具处理JSON文件

---

## 🆘 常见问题

### Q1: 如何知道新记忆系统是否启用？
A: 日志中会显示 "学生Agent初始化: xxx, 使用新记忆系统: True"

### Q2: 可以不使用新记忆系统吗？
A: 可以，不加`--use-new-memory`标志即可使用旧系统

### Q3: 温度参数如何选择？
A: 0.5-1.5之间，1.0为平衡值，越低越聚焦，越高越多样

### Q4: 测试卡住怎么办？
A: 先运行`test_simple_integration.py`，它不会卡住

---

## 🎉 开始你的实验

```bash
# 复制并运行这条命令
python main.py --experiment semester --use-new-memory

# 或者使用你喜欢的参数
python main.py --experiment semester \
    --course-name "你的课程" \
    --student-count 20 \
    --use-new-memory
```

**祝实验成功！** 🚀

---

**版本**: 1.0  
**更新时间**: 2025年10月20日  
**状态**: ✅ 生产就绪
