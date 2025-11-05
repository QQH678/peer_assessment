
# 增强版同伴互评教学模拟系统 (Enhanced Peer Assessment Teaching Simulation System)

## 项目概述

这是一个模拟高校计算机类课程完整教学过程的智能代理系统。系统不仅能够模拟同伴互评过程，还集成了**全新的三维记忆系统**和**教师智能分析**，能够：

- **教师功能**：设计课程体系、规划知识点、创建分阶段作业、智能分析学生学习状态
- **学生模拟**：具备三维记忆（学习/评价/被评价）的智能学生，基于温度参数检索历史经验
- **教学过程**：完整的学期教学模拟，包含多个阶段的循序渐进学习
- **互评系统**：模拟真实的同伴互评过程，记录评价经验
- **数据分析**：收集和分析教学效果数据，生成学情报告

## 🆕 最新功能特性 (v2.0)

### 🧠 新记忆系统
- **三维记忆结构**
  - `LEARNING`: 学习情况记忆 (作业完成、知识掌握)
  - `PEER_EVALUATION`: 评价他人记忆 (评价经验、评分标准)
  - `RECEIVED_EVALUATION`: 被评价记忆 (他人反馈、改进方向)
  - `TEACHER_FEEDBACK`: 教师反馈记忆 (指导建议、知识状态)

- **温度参数检索** (借鉴知识蒸馏)
  - 优先级计算: 0.4×相关性 + 0.2×时新性 + 0.3×重要性 + 0.1×成功度
  - Softmax温度调控: 平衡探索与利用
  - 自适应温度: 根据轮次和记忆状态动态调整

- **长短期记忆划分**
  - 短期记忆 (STM): 最大50条，工作记忆区
  - 长期记忆 (LTM): 最大200条，巩固知识区
  - 自动巩固: 访问次数≥3时转为长期记忆
  - 智能修剪: 低优先级记忆自动清理

### 🎓 教师智能分析
- **每轮智能分析**
  - 知识状态: 掌握程度、强项、弱项、学习轨迹
  - 元认知评估: 自我认知准确性、反思深度、学习策略
  - 互评质量: 评分合理性、反馈建设性、改进建议质量

- **阶段学情报告**
  - 整体学习表现汇总
  - 互评活动质量分析
  - 个性化改进建议
  - 教学干预建议

- **可配置互评参数**
  - `rounds_per_stage`: 每阶段轮次数
  - `peers_per_round`: 每轮评价同伴数
  - `memory_base_temperature`: 记忆检索温度

### ⚡ 技术亮点
- **GPU加速**: CUDA支持的FAISS高性能向量检索
- **语义检索**: 多语言语义模型 (paraphrase-multilingual-MiniLM-L12-v2)
- **LLM集成**: 自然的反思和评价生成 (Qwen2.5-7B)
- **记忆巩固**: 模拟Ebbinghaus遗忘曲线
- **100%测试覆盖**: 完整的集成测试验证

## 🚀 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行新记忆系统实验
```bash
# 使用默认配置
python main.py --mode new_memory

# 自定义参数
python main.py --mode new_memory \
    --rounds-per-stage 3 \
    --peers-per-round 2 \
    --memory-temperature 1.0 \
    --use-new-memory \
    --enable-teacher-analysis
```

### 运行集成测试
```bash
python test_integration_complete.py
```

## 📚 完整文档

### 快速指南 (必读)
- **[QUICKSTART.md](./QUICKSTART.md)** - 快速启动指南 ⭐
- **[FINAL_INTEGRATION_SUMMARY.md](./FINAL_INTEGRATION_SUMMARY.md)** - 集成完成总结 ⭐
- **[DOCUMENTATION_INDEX.md](./DOCUMENTATION_INDEX.md)** - 文档索引和阅读指南

### 技术文档
- **[NEW_MEMORY_DESIGN.md](./NEW_MEMORY_DESIGN.md)** - 系统架构设计
- **[NEW_SYSTEM_USAGE_GUIDE.md](./NEW_SYSTEM_USAGE_GUIDE.md)** - 详细使用指南
- **[INTEGRATION_GUIDE.md](./INTEGRATION_GUIDE.md)** - 开发者集成指南
- **[IMPLEMENTATION_SUMMARY.md](./IMPLEMENTATION_SUMMARY.md)** - 实现技术总结
- **[INTEGRATION_TEST_REPORT.md](./INTEGRATION_TEST_REPORT.md)** - 集成测试报告

## 系统架构

```
peer_assessment/
├── agents/                 # 智能代理模块
│   ├── teachers/          # 教师代理 (含智能分析器)
│   │   ├── teacher_agent.py      # 教师Agent (已集成)
│   │   └── teacher_analyzer.py   # 智能分析器 (~600行)
│   ├── students/          # 学生代理 (含新记忆系统)
│   │   └── student_agent.py      # 学生Agent (已集成, +400行)
│   ├── assignments/       # 作业生成代理
│   └── evaluators/        # 评估代理
├── memory/                # 🆕 新记忆系统
│   ├── new_memory_models.py      # 记忆数据模型 (~400行)
│   ├── new_memory_system.py      # 记忆系统核心 (~600行)
│   ├── semantic_retrieval.py     # 语义检索引擎
│   ├── vector_retrieval.py       # 向量检索
│   └── experience_replay.py      # 经验回放
├── models/                # 数据模型
├── simulation/            # 模拟器
├── config/                # 配置文件
│   ├── peer_review_config.py     # 🆕 互评配置助手
│   └── settings.py               # 全局配置 (已更新)
├── data/                  # 数据存储
├── utils/                 # 工具函数
├── analysis/              # 数据分析
├── main.py                # 🆕 主程序 (已集成新参数)
└── test_integration_complete.py  # 🆕 集成测试
```

## 功能特性

### 学生类型模拟
- **优秀学生**：学习能力强，记忆巩固快，评价客观准确
- **普通学生**：中等水平，正常的记忆模式，评价相对客观
- **基础较弱学生**：理解有限，记忆巩固较慢，评价可能不够准确
- **严格学生**：评价标准较高，给分偏严
- **宽松学生**：评价标准较低，给分偏高

### 课程模型
- **知识点体系**：具有前置关系的知识点网络
- **难度分级**：1-5级难度分级，循序渐进
- **教学阶段**：按周次划分的教学阶段，每个阶段包含相关知识点
- **学习目标**：明确的阶段性和总体学习目标

### 作业类型
- 编程作业（算法、数据结构等）
- 项目作品（Web应用、移动应用等）
- 设计文档（系统设计、架构设计等）
- 研究报告（技术调研、实验报告等）

### 评价维度
- 功能实现（40%）
- 代码质量（30%）
- 创新性（15%）
- 文档完整性（15%）

## 使用指南

### 基本使用

1. **传统同伴互评模拟**
```bash
# 基础模拟
python main.py --experiment basic

# 大规模模拟
python main.py --experiment large_scale

# 偏差分析模拟
python main.py --experiment bias_analysis
```

2. **🆕 学期教学模拟**
```bash
# 默认学期教学模拟（使用新记忆系统）
python main.py --experiment semester --use-new-memory --enable-teacher-analysis

# 高级多课程模拟
python main.py --experiment advanced_semester

# 自定义学期模拟（完整参数）
python main.py --experiment semester \
    --course-name "数据结构与算法" \
    --subject "计算机科学" \
    --student-count 30 \
    --duration-weeks 16 \
    --evaluations-per-work 4 \
    --rounds-per-stage 3 \
    --peers-per-round 2 \
    --memory-temperature 1.0 \
    --use-new-memory \
    --enable-teacher-analysis
```
# 简化版 (推荐用于测试)
python main.py --experiment semester \
    --course-name "数据结构与算法" \
    --subject "计算机科学" \
    --student-count 4 \
    --duration-weeks 16 \
    --evaluations-per-work 4 \
    --rounds-per-stage 2 \
    --peers-per-round 2 \
    --use-new-memory \
    --enable-teacher-analysis
```

### 🆕 综合学情报告生成

学期模拟完成后，系统会自动为每位学生生成综合学情报告：

```bash
# 报告位置
cd data/semester_<id>/comprehensive_reports/

# 包含以下文件：
# - report_<student_id>.json    # 完整数据
# - report_<student_id>.md      # 人类可读格式
# - visualization_prompt_<student_id>.txt  # V0可视化Prompt
```

**报告内容：**
- 📝 文字评价：总体评价、分项评价、优势与成就、改进建议
- 📊 数据可视化：成绩趋势、知识掌握雷达图、元认知发展曲线等
- 🎨 V0集成：可直接复制Prompt到 https://v0.dev 生成交互式Dashboard

**详细文档：**
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 快速参考
- [COMPREHENSIVE_REPORT_GUIDE.md](./COMPREHENSIVE_REPORT_GUIDE.md) - 完整指南

**快速演示：**
```bash
python demo_comprehensive_report.py --mode quick

3. **🆕 系统演示**
```bash
# 运行完整功能演示
python demo_teacher_system.py
```

### 高级功能

- **个性化学习**：学生会根据自己的记忆状况和知识掌握程度来完成作业
- **知识传承**：后续作业会考虑学生在前期作业中的学习情况
- **教学适应**：教师会根据学生表现调整作业难度和提示
- **记忆建模**：真实模拟人类的记忆特性，包括遗忘和巩固

### 配置选项

在 `.env` 文件中可配置：

```env
# OpenAI API配置
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-3.5-turbo

# 🆕 教师Agent配置
COURSE_DESIGN_TEMPERATURE=0.3
ASSIGNMENT_CREATION_TEMPERATURE=0.4

# 🆕 记忆系统配置
SHORT_TERM_MEMORY_DECAY=0.1
LONG_TERM_MEMORY_THRESHOLD=0.6
MEMORY_CONSOLIDATION_THRESHOLD=0.7
```

## 数据输出

### 传统模拟输出
- `data/session_*/` - 传统的互评模拟会话数据

### 🆕 学期模拟输出
- `data/semester_*/course.json` - 课程设计数据
- `data/semester_*/students.json` - 学生信息（包含记忆状态）
- `data/semester_*/assignments.json` - 分阶段作业数据
- `data/semester_*/works.json` - 学生作品
- `data/semester_*/evaluations.json` - 互评记录
- `data/semester_*/statistics.json` - 统计分析

## 实验建议

### 教学效果研究
1. **知识点掌握分析**：比较不同教学阶段设计对学生知识掌握的影响
2. **记忆巩固研究**：分析不同类型学生的记忆巩固模式
3. **个性化教学**：研究基于记忆状况的个性化作业设计效果

### 互评质量分析  
1. **学习历程影响**：分析学生的学习历程对互评质量的影响
2. **知识水平差异**：研究不同知识掌握程度学生之间的互评效果
3. **阶段性变化**：跟踪学生在整个学期中互评能力的变化

### 环境要求
- Python 3.8+
- OpenAI API (或其他LLM API)

### 安装依赖
```bash
pip install -r requirements.txt
```

### 运行示例
```bash
python main.py --experiment basic_simulation
```

## 数据输出

系统会生成以下类型的数据：
- 学生作品数据
- 互评结果数据
- 评价过程数据
- 统计分析报告
