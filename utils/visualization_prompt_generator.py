"""
可视化Prompt生成器
将学生数据转换为V0可用的可视化组件提示词
"""

from typing import Dict, Any, List
import json


class VisualizationPromptGenerator:
    """生成用于V0的可视化提示词"""
    
    def generate_student_report_prompt(
        self,
        student: Any,
        performance_data: Any,
        text_evaluation: Dict[str, Any]
    ) -> str:
        """
        生成学生学情报告的可视化Prompt
        
        Args:
            student: 学生对象
            performance_data: 学生表现数据
            text_evaluation: 文字评价
            
        Returns:
            str: V0可用的提示词
        """
        
        # 准备数据
        student_name = performance_data.student_name
        course_name = "课程"  # 从上下文获取
        
        # 构建详细的可视化需求prompt
        prompt = f"""请创建一个现代化的、交互式的学生学情报告Dashboard页面。

## 报告信息
- 学生姓名：{student_name}
- 专业：{performance_data.major}
- GPA：{performance_data.gpa}
- 学生类型：{performance_data.student_type}

## 设计要求

### 1. 整体布局
- 使用响应式设计，支持桌面和移动端
- 采用卡片式布局，信息层次清晰
- 配色方案：专业、温暖，主色调使用蓝色系
- 使用shadcn/ui组件库构建

### 2. 必需的可视化组件

#### 顶部概览卡片
显示以下核心指标（使用大数字+图标）：
- 平均成绩：{performance_data.average_score:.1f}分
- 完成作业数：{len(performance_data.assignment_scores)}个
- 参与互评：{performance_data.evaluations_given_count}次
- 元认知增长：{performance_data.metacognition_growth:+.1f}

#### 成绩趋势图（折线图）
- 数据：{json.dumps([{'assignment': i+1, 'score': s['score']} for i, s in enumerate(performance_data.assignment_scores)])}
- 显示成绩的变化趋势
- 趋势标识：{performance_data.score_trend}（用颜色和图标表示：上升-绿色↗️，下降-红色↘️，稳定-蓝色→）
- 使用recharts库绘制

#### 知识掌握雷达图
- 数据：各知识点的掌握度
- 知识点列表（取前8个）：{json.dumps(list(performance_data.final_knowledge_mastery.items())[:8])}
- 使用recharts的RadarChart
- 显示最终掌握水平
- 用不同颜色区分掌握程度（高：绿色，中：黄色，低：红色）

#### 知识增长柱状图
- 数据：各知识点的增长率
- 显示增长最多的前5个知识点
- 数据：{json.dumps(sorted(performance_data.knowledge_growth_rate.items(), key=lambda x: x[1], reverse=True)[:5] if performance_data.knowledge_growth_rate else [])}
- 使用recharts的BarChart
- 正增长用绿色，负增长用红色

#### 元认知发展曲线
- 数据：{json.dumps([{'round': i+1, 'score': score} for i, score in enumerate(performance_data.metacognition_scores)])}
- 使用折线图展示元认知能力的发展轨迹
- 标注起点和终点
- 显示增长值：{performance_data.metacognition_growth:+.2f}

#### 互评统计饼图
- 数据：
  - 给出评价：{performance_data.evaluations_given_count}
  - 收到评价：{performance_data.evaluations_received_count}
- 使用recharts的PieChart
- 展示互评参与情况

#### 学习行为仪表盘
- 参与度：{performance_data.participation_level}
- 稳定性：{performance_data.consistency_score:.1%}
- 使用进度条或仪表盘组件

### 3. 文字评价部分

使用Accordion（手风琴）组件展示以下内容：

#### 总体评价（默认展开）
```
{text_evaluation.get('overall_assessment', '')}
```

#### 分项评价
- 知识掌握：{text_evaluation.get('knowledge_assessment', '')}
- 技能发展：{text_evaluation.get('skill_assessment', '')}
- 学习态度：{text_evaluation.get('attitude_assessment', '')}
- 同伴互动：{text_evaluation.get('peer_interaction_assessment', '')}

#### 优势与亮点
{json.dumps(text_evaluation.get('strengths', []), ensure_ascii=False)}
展示为带图标的列表（使用✓或星星图标）

#### 成就展示
{json.dumps(text_evaluation.get('achievements', []), ensure_ascii=False)}
使用徽章（Badge）组件展示

#### 需要改进的方面
{json.dumps(text_evaluation.get('weaknesses', []), ensure_ascii=False)}
展示为列表，语气温和

#### 改进建议
{json.dumps(text_evaluation.get('improvement_suggestions', []), ensure_ascii=False)}
每条建议配上小图标（💡）

#### 未来发展建议
```
{text_evaluation.get('future_recommendations', '')}
```
使用Alert组件高亮显示

#### 推荐学习资源
{json.dumps(text_evaluation.get('recommended_resources', []), ensure_ascii=False)}
展示为链接列表（虽然这里不是真实链接）

### 4. 交互功能
- 所有图表支持hover显示详细数据
- 可以切换不同的视图（概览/详细数据）
- 可以导出报告（添加导出按钮，模拟功能即可）
- 可以打印报告（添加打印按钮）

### 5. 技术栈
- React + TypeScript
- shadcn/ui 组件库
- recharts 图表库
- Tailwind CSS 样式
- Lucide React 图标库

### 6. 样式要求
- 使用柔和的阴影效果
- 卡片之间有适当的间距
- 图表使用渐变色
- 响应式布局（使用grid或flex）
- 深色模式支持（可选）

### 7. 动画效果
- 组件加载时有淡入动画
- 数字跳动效果
- 图表绘制动画

## 预期效果
创建一个专业、美观、信息丰富的学生学情报告页面，教师可以一目了然地了解学生的整体表现，学生也能清晰地看到自己的学习成果和需要改进的方向。

请生成完整的React组件代码。
"""
        
        return prompt
    
    def generate_semester_summary_prompt(
        self,
        semester_data: Dict[str, Any],
        all_students_summary: List[Dict[str, Any]]
    ) -> str:
        """
        生成学期整体总结的可视化Prompt
        
        Args:
            semester_data: 学期数据
            all_students_summary: 所有学生的汇总数据
            
        Returns:
            str: V0可用的提示词
        """
        
        prompt = f"""请创建一个学期教学总结Dashboard页面。

## 学期信息
- 课程名称：{semester_data.get('course_name', '未知课程')}
- 学期ID：{semester_data.get('semester_id', '')}
- 学生人数：{len(all_students_summary)}
- 教学阶段数：{semester_data.get('total_stages', 0)}

## 设计要求

### 1. 整体概览卡片
显示关键统计数据：
- 学生总数
- 作业总数
- 互评总次数
- 平均完成率

### 2. 班级成绩分布图
- 使用直方图展示成绩分布
- 标注平均分、中位数
- 显示优秀率、及格率

### 3. 学生类型分布
- 使用饼图展示不同类型学生的比例
- 各类型学生的平均表现

### 4. 知识点掌握情况
- 热力图展示全班在各知识点上的掌握情况
- 识别全班掌握较好和较差的知识点

### 5. 互评质量分析
- 互评次数分布
- 互评质量统计
- 最活跃的评价者

### 6. 学习进步榜
- Top 10进步最大的学生
- 使用条形图展示

### 7. 各阶段表现对比
- 折线图展示各阶段的平均成绩变化
- 识别教学效果最好的阶段

使用与学生报告相同的技术栈和设计风格。
"""
        
        return prompt
    
    def generate_comparison_prompt(
        self,
        students_data: List[Dict[str, Any]]
    ) -> str:
        """
        生成多个学生对比的可视化Prompt
        
        Args:
            students_data: 多个学生的数据
            
        Returns:
            str: V0可用的提示词
        """
        
        student_names = [s.get('name', f"学生{i+1}") for i, s in enumerate(students_data[:5])]
        
        prompt = f"""请创建一个学生对比分析页面。

## 对比学生
{json.dumps(student_names, ensure_ascii=False)}

## 设计要求

### 1. 选择器
- 允许用户选择2-5个学生进行对比
- 使用多选下拉框或复选框

### 2. 对比维度
- 平均成绩对比（柱状图）
- 知识掌握对比（雷达图，多个学生重叠显示）
- 学习进度对比（折线图，多条线）
- 互评参与度对比（柱状图）
- 元认知发展对比（折线图）

### 3. 差异分析
- 自动识别各学生的优势领域
- 标注显著差异的指标
- 提供简短的对比总结

使用表格+图表的混合展示方式，支持导出对比报告。
"""
        
        return prompt
