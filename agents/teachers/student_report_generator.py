"""
学生综合学情报告生成器
教师Agent使用此模块为每位学生生成包含文字评价和数据分析的综合报告
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import json
import logging
import openai
from config.settings import Config


class StudentPerformanceData(BaseModel):
    """学生表现数据汇总"""
    student_id: str
    student_name: str
    
    # 基本信息
    student_type: str
    major: str
    gpa: float
    
    # 知识掌握情况
    knowledge_mastery_history: List[Dict[str, float]] = Field(description="各阶段知识掌握度")
    final_knowledge_mastery: Dict[str, float] = Field(description="最终知识掌握度")
    knowledge_growth_rate: Dict[str, float] = Field(description="知识点增长率")
    
    # 作业完成情况
    assignment_scores: List[Dict[str, Any]] = Field(description="作业成绩列表")
    average_score: float
    score_trend: str = Field(description="上升/稳定/下降")
    
    # 互评表现
    evaluations_given_count: int
    evaluations_received_count: int
    avg_evaluation_quality: float = Field(description="给出评价的平均质量")
    avg_received_score: float = Field(description="收到的平均分数")
    
    # 元认知发展
    metacognition_scores: List[float] = Field(description="各轮元认知分数")
    metacognition_growth: float
    
    # 学习行为
    participation_level: str = Field(description="积极/一般/消极")
    consistency_score: float = Field(description="稳定性得分")
    
    # 阶段报告摘要
    stage_reports: List[Dict[str, Any]] = Field(description="各阶段学情报告")


class ComprehensiveStudentReport(BaseModel):
    """综合学情报告"""
    report_id: str
    student_id: str
    student_name: str
    course_name: str
    semester_id: str
    
    # 报告生成信息
    generated_at: datetime = Field(default_factory=datetime.now)
    teacher_name: str = "AI教师"
    
    # === 文字评价部分 ===
    
    # 总体评价
    overall_assessment: str = Field(description="总体学习表现评价，3-5段")
    
    # 分项评价
    knowledge_assessment: str = Field(description="知识掌握评价")
    skill_assessment: str = Field(description="技能发展评价") 
    attitude_assessment: str = Field(description="学习态度评价")
    peer_interaction_assessment: str = Field(description="同伴互动评价")
    
    # 亮点与优势
    strengths: List[str] = Field(description="学生的优势和亮点")
    achievements: List[str] = Field(description="本学期的重要成就")
    
    # 不足与改进
    weaknesses: List[str] = Field(description="需要改进的方面")
    improvement_suggestions: List[str] = Field(description="具体改进建议")
    
    # 未来发展建议
    future_recommendations: str = Field(description="对未来学习的建议")
    recommended_resources: List[str] = Field(description="推荐学习资源")
    
    # === 数据部分（用于可视化） ===
    performance_data: StudentPerformanceData
    
    # === V0可视化Prompt ===
    visualization_prompt: str = Field(description="传给V0的可视化提示词")
    
    
class StudentReportGenerator:
    """学生报告生成器"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        logging.info("学生报告生成器初始化完成")
    
    def generate_comprehensive_report(
        self,
        student: Any,
        semester_data: Dict[str, Any],
        stage_reports: List[Dict[str, Any]],
        course_info: Dict[str, Any]
    ) -> ComprehensiveStudentReport:
        """
        生成学生综合学情报告
        
        Args:
            student: 学生对象
            semester_data: 学期数据（作业、互评等）
            stage_reports: 各阶段学情报告
            course_info: 课程信息
            
        Returns:
            ComprehensiveStudentReport: 综合报告
        """
        student_name = student.get('name') if isinstance(student, dict) else student.name
        logging.info(f"开始生成学生 {student_name} 的综合学情报告")
        
        # 1. 收集并整理学生数据
        performance_data = self._collect_performance_data(
            student, semester_data, stage_reports
        )
        
        # 2. 使用LLM生成文字评价
        text_evaluation = self._generate_text_evaluation(
            student, performance_data, course_info
        )
        
        # 3. 生成可视化Prompt
        from utils.visualization_prompt_generator import VisualizationPromptGenerator
        viz_generator = VisualizationPromptGenerator()
        visualization_prompt = viz_generator.generate_student_report_prompt(
            student, performance_data, text_evaluation
        )
        
        # 4. 组装综合报告
        student_id = student.get('id') if isinstance(student, dict) else student.id
        student_name = student.get('name') if isinstance(student, dict) else student.name
        
        report = ComprehensiveStudentReport(
            report_id=f"report_{student_id}_{semester_data['semester_id']}",
            student_id=student_id,
            student_name=student_name,
            course_name=course_info.get('course_name', '未知课程'),
            semester_id=semester_data['semester_id'],
            
            # 文字评价
            overall_assessment=text_evaluation['overall_assessment'],
            knowledge_assessment=text_evaluation['knowledge_assessment'],
            skill_assessment=text_evaluation['skill_assessment'],
            attitude_assessment=text_evaluation['attitude_assessment'],
            peer_interaction_assessment=text_evaluation['peer_interaction_assessment'],
            
            strengths=text_evaluation['strengths'],
            achievements=text_evaluation['achievements'],
            weaknesses=text_evaluation['weaknesses'],
            improvement_suggestions=text_evaluation['improvement_suggestions'],
            future_recommendations=text_evaluation['future_recommendations'],
            recommended_resources=text_evaluation['recommended_resources'],
            
            # 数据部分
            performance_data=performance_data,
            
            # 可视化Prompt
            visualization_prompt=visualization_prompt
        )
        
        logging.info(f"学生 {student_name} 的综合报告生成完成")
        return report
    
    def _collect_performance_data(
        self,
        student: Any,
        semester_data: Dict[str, Any],
        stage_reports: List[Dict[str, Any]]
    ) -> StudentPerformanceData:
        """收集学生表现数据"""
        
        # 获取学生ID
        student_id = student.id if hasattr(student, 'id') else student['id']
        
        # 收集知识掌握历史
        knowledge_history = []
        for report in stage_reports:
            if isinstance(report, dict):
                knowledge_history.append(report.get('final_knowledge_mastery', {}))
            else:
                knowledge_history.append(report.final_knowledge_mastery)
        
        # 最终知识掌握度
        final_mastery = knowledge_history[-1] if knowledge_history else {}
        
        # 计算增长率
        growth_rate = {}
        if len(knowledge_history) >= 2:
            initial = knowledge_history[0]
            final = knowledge_history[-1]
            for kp_id in final.keys():
                initial_val = initial.get(kp_id, 0.0)
                final_val = final.get(kp_id, 0.0)
                if initial_val > 0:
                    growth_rate[kp_id] = (final_val - initial_val) / initial_val
                else:
                    growth_rate[kp_id] = final_val
        
        # 收集该学生的所有作业ID和work_id映射
        student_works = {}  # work_id -> work_info
        for work in semester_data.get('works', []):
            if work.get('student_id') == student_id:
                student_works[work.get('id')] = {
                    'assignment_id': work.get('assignment_id'),
                    'submission_time': work.get('submission_time'),
                    'evaluations': []  # 存储该作业收到的所有评价
                }
        
        # 统计互评
        evals_given = [e for e in semester_data.get('evaluations', []) 
                      if e.get('evaluator_id') == student_id]
        evals_received = [e for e in semester_data.get('evaluations', [])
                         if e.get('work_id') in student_works.keys()]
        
        # 将收到的评价分配到对应的作业
        for evaluation in evals_received:
            work_id = evaluation.get('work_id')
            if work_id in student_works:
                student_works[work_id]['evaluations'].append(evaluation)
        
        # 计算每个作业的平均分数
        assignment_scores = []
        total_score = 0
        for work_id, work_info in student_works.items():
            evaluations = work_info['evaluations']
            
            if evaluations:
                # 计算该作业的平均分（从所有评价的scores中计算）
                work_total_score = 0
                for evaluation in evaluations:
                    scores = evaluation.get('scores', {})
                    # 计算单个评价的总分
                    eval_score = sum([
                        scores.get('functionality', 0),
                        scores.get('code_quality', 0),
                        scores.get('innovation', 0),
                        scores.get('documentation', 0)
                    ])
                    work_total_score += eval_score
                
                work_avg_score = work_total_score / len(evaluations)
            else:
                work_avg_score = 0
            
            assignment_scores.append({
                'assignment_id': work_info['assignment_id'],
                'score': work_avg_score,
                'submission_time': work_info['submission_time']
            })
            total_score += work_avg_score
        
        avg_score = total_score / len(assignment_scores) if assignment_scores else 0
        
        # 判断成绩趋势
        score_trend = "稳定"
        if len(assignment_scores) >= 2:
            first_half_avg = sum(s['score'] for s in assignment_scores[:len(assignment_scores)//2]) / (len(assignment_scores)//2)
            second_half_avg = sum(s['score'] for s in assignment_scores[len(assignment_scores)//2:]) / (len(assignment_scores) - len(assignment_scores)//2)
            if second_half_avg > first_half_avg * 1.1:
                score_trend = "上升"
            elif second_half_avg < first_half_avg * 0.9:
                score_trend = "下降"
        
        # 元认知发展
        metacog_scores = []
        for report in stage_reports:
            if isinstance(report, dict):
                trajectory = report.get('metacognition_trajectory', [])
                if trajectory:
                    metacog_scores.extend([score for _, score in trajectory])
            else:
                trajectory = report.metacognition_trajectory
                if trajectory:
                    metacog_scores.extend([score for _, score in trajectory])
        
        metacog_growth = 0
        if len(metacog_scores) >= 2:
            metacog_growth = metacog_scores[-1] - metacog_scores[0]
        
        # 计算评价质量（从阶段报告中获取）
        avg_evaluation_quality = 0.75  # 默认值
        if stage_reports:
            eval_qualities = []
            for report in stage_reports:
                if isinstance(report, dict):
                    trajectory = report.get('evaluation_quality_trajectory', [])
                    if trajectory:
                        # trajectory 是 [(round, quality), ...]
                        eval_qualities.extend([quality for _, quality in trajectory])
                else:
                    trajectory = getattr(report, 'evaluation_quality_trajectory', [])
                    if trajectory:
                        eval_qualities.extend([quality for _, quality in trajectory])
            
            if eval_qualities:
                avg_evaluation_quality = sum(eval_qualities) / len(eval_qualities)
        
        # 计算稳定性分数（基于作业分数的方差）
        consistency_score = 0.8  # 默认值
        if len(assignment_scores) >= 2:
            scores_list = [s['score'] for s in assignment_scores]
            mean_score = sum(scores_list) / len(scores_list)
            variance = sum((s - mean_score) ** 2 for s in scores_list) / len(scores_list)
            std_dev = variance ** 0.5
            # 稳定性分数：方差越小越稳定，归一化到0-1之间
            # 假设分数范围是0-100，标准差>20认为不稳定
            if mean_score > 0:
                consistency_score = max(0, 1 - (std_dev / 20))
            else:
                consistency_score = 1.0  # 都是0分也算"稳定"
        
        # 构建数据对象
        return StudentPerformanceData(
            student_id=student_id,
            student_name=student.name if hasattr(student, 'name') else student['name'],
            student_type=str(student.student_type if hasattr(student, 'student_type') else student.get('student_type')),
            major=student.major if hasattr(student, 'major') else student.get('major', '未知'),
            gpa=student.gpa if hasattr(student, 'gpa') else student.get('gpa', 0.0),
            
            knowledge_mastery_history=knowledge_history,
            final_knowledge_mastery=final_mastery,
            knowledge_growth_rate=growth_rate,
            
            assignment_scores=assignment_scores,
            average_score=avg_score,
            score_trend=score_trend,
            
            evaluations_given_count=len(evals_given),
            evaluations_received_count=len(evals_received),
            avg_evaluation_quality=avg_evaluation_quality,
            avg_received_score=avg_score,
            
            metacognition_scores=metacog_scores,
            metacognition_growth=metacog_growth,
            
            participation_level="积极" if len(evals_given) > 5 else "一般",
            consistency_score=consistency_score,
            
            stage_reports=[r if isinstance(r, dict) else r.dict() for r in stage_reports]
        )
    
    def _generate_text_evaluation(
        self,
        student: Any,
        performance_data: StudentPerformanceData,
        course_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用LLM生成文字评价"""
        
        # 构建评价提示词
        prompt = f"""作为一名经验丰富的教师，请为学生"{performance_data.student_name}"撰写一份综合学情报告。

【学生基本信息】
- 专业：{performance_data.major}
- GPA：{performance_data.gpa}
- 学生类型：{performance_data.student_type}

【课程信息】
- 课程名称：{course_info.get('course_name')}
- 课程主题：{course_info.get('subject')}

【学习表现数据】
1. 知识掌握情况：
   - 最终掌握的知识点数：{len(performance_data.final_knowledge_mastery)}
   - 平均掌握度：{sum(performance_data.final_knowledge_mastery.values()) / len(performance_data.final_knowledge_mastery) if performance_data.final_knowledge_mastery else 0:.2f}
   - 进步最快的领域：{sorted(performance_data.knowledge_growth_rate.items(), key=lambda x: x[1], reverse=True)[:3] if performance_data.knowledge_growth_rate else []}

2. 作业表现：
   - 完成作业数：{len(performance_data.assignment_scores)}
   - 平均成绩：{performance_data.average_score:.2f}
   - 成绩趋势：{performance_data.score_trend}

3. 互评表现：
   - 给出评价：{performance_data.evaluations_given_count}次
   - 收到评价：{performance_data.evaluations_received_count}次
   - 参与度：{performance_data.participation_level}

4. 元认知发展：
   - 元认知增长：{performance_data.metacognition_growth:.2f}

请按以下JSON格式返回评价：
{{
    "overall_assessment": "总体评价（3-5段，200-400字，要具体、有温度、有建设性）",
    "knowledge_assessment": "知识掌握评价（分析掌握好的和需要加强的知识点）",
    "skill_assessment": "技能发展评价（编程能力、问题解决能力等）",
    "attitude_assessment": "学习态度评价（参与度、主动性、坚持性等）",
    "peer_interaction_assessment": "同伴互动评价（互评质量、协作精神等）",
    
    "strengths": ["优势1", "优势2", "优势3"],
    "achievements": ["成就1", "成就2"],
    "weaknesses": ["不足1", "不足2"],
    "improvement_suggestions": ["建议1", "建议2", "建议3"],
    
    "future_recommendations": "未来发展建议（针对性、可操作的建议，150-250字）",
    "recommended_resources": ["资源1", "资源2", "资源3"]
}}

要求：
1. 评价要客观、具体、有数据支撑
2. 语言要温暖、鼓励，但不夸大
3. 建议要具体、可操作
4. 要体现个性化，避免模板化
5. 确保返回有效的JSON格式
"""

        try:
            response = self.client.chat.completions.create(
                model=Config.DEFAULT_MODEL,
                messages=[
                    {"role": "system", "content": "你是一名富有经验和同理心的教师，擅长撰写个性化、有温度的学生评价。请严格按照JSON格式返回结果。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            # 清理响应
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            
            evaluation = json.loads(content)
            return evaluation
            
        except Exception as e:
            logging.error(f"生成文字评价失败: {e}")
            # 返回默认评价
            return {
                "overall_assessment": f"{performance_data.student_name}同学在本学期表现良好，完成了{len(performance_data.assignment_scores)}次作业，平均成绩{performance_data.average_score:.1f}分。",
                "knowledge_assessment": "知识掌握情况整体良好。",
                "skill_assessment": "技能发展稳步提升。",
                "attitude_assessment": "学习态度认真。",
                "peer_interaction_assessment": "同伴互动表现积极。",
                "strengths": ["学习认真", "积极参与"],
                "achievements": ["完成所有作业"],
                "weaknesses": ["需要进一步提升"],
                "improvement_suggestions": ["继续保持", "加强练习"],
                "future_recommendations": "继续努力，持续进步。",
                "recommended_resources": ["课程教材", "在线教程"]
            }
    
    def save_report_to_file(self, report: ComprehensiveStudentReport, output_dir: str):
        """保存报告到文件"""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存JSON格式
        json_file = os.path.join(output_dir, f"report_{report.student_id}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(report.dict(), f, ensure_ascii=False, indent=2, default=str)
        
        # 保存Markdown格式（人类可读）
        md_file = os.path.join(output_dir, f"report_{report.student_id}.md")
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(self._format_report_as_markdown(report))
        
        # 保存可视化Prompt（单独文件，方便复制给V0）
        prompt_file = os.path.join(output_dir, f"visualization_prompt_{report.student_id}.txt")
        with open(prompt_file, 'w', encoding='utf-8') as f:
            f.write(report.visualization_prompt)
        
        logging.info(f"报告已保存: {json_file}, {md_file}, {prompt_file}")
    
    def _format_report_as_markdown(self, report: ComprehensiveStudentReport) -> str:
        """将报告格式化为Markdown"""
        md = f"""# 综合学情报告

## 基本信息
- **学生姓名**：{report.student_name}
- **课程名称**：{report.course_name}
- **学期ID**：{report.semester_id}
- **报告生成时间**：{report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}
- **教师**：{report.teacher_name}

---

## 总体评价

{report.overall_assessment}

---

## 分项评价

### 知识掌握
{report.knowledge_assessment}

### 技能发展
{report.skill_assessment}

### 学习态度
{report.attitude_assessment}

### 同伴互动
{report.peer_interaction_assessment}

---

## 优势与成就

### 优势
{chr(10).join(f"- {s}" for s in report.strengths)}

### 本学期成就
{chr(10).join(f"- {a}" for a in report.achievements)}

---

## 改进方向

### 需要关注的方面
{chr(10).join(f"- {w}" for w in report.weaknesses)}

### 改进建议
{chr(10).join(f"- {s}" for s in report.improvement_suggestions)}

---

## 未来发展建议

{report.future_recommendations}

### 推荐学习资源
{chr(10).join(f"- {r}" for r in report.recommended_resources)}

---

## 学习数据概览

- **平均成绩**：{report.performance_data.average_score:.2f}
- **成绩趋势**：{report.performance_data.score_trend}
- **完成作业数**：{len(report.performance_data.assignment_scores)}
- **参与互评**：{report.performance_data.evaluations_given_count}次
- **收到互评**：{report.performance_data.evaluations_received_count}次
- **元认知增长**：{report.performance_data.metacognition_growth:+.2f}

---

*报告ID: {report.report_id}*
"""
        return md
