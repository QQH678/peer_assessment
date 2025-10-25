from typing import Dict, List, Any, Optional
import openai
from models.data_models import Course, KnowledgePoint, TeachingStage, Assignment
from config.settings import Config
from config.peer_review_config import PeerReviewConfig
from agents.teachers.teacher_analyzer import TeacherAnalyzer
from memory.new_memory_models import TeacherFeedbackMemory
import json
import logging
import uuid

class TeacherAgent:
    """教师代理，负责课程设计、知识点规划、阶段性教学和学生分析"""
    
    def __init__(self, config: Optional[PeerReviewConfig] = None):
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        
        # 互评配置
        self.config = config or PeerReviewConfig()
        
        # 教师分析器
        self.analyzer = TeacherAnalyzer()
        
        logging.info(f"教师Agent初始化完成，互评配置：每阶段{self.config.rounds_per_stage}轮")
    
    def design_course(self, course_name: str, subject: str, duration_weeks: int = 16) -> 'Course':
        """设计完整的课程体系"""
        print(f"正在为 {course_name} 设计课程体系...")
        
        # 构建课程设计提示词
        prompt = f"""作为一名经验丰富的{subject}教师，请为"{course_name}"课程设计一个完整的{duration_weeks}周教学计划。

请分析以下要求：
1. 将课程分解为核心知识点，每个知识点应该有明确的学习目标
2. 知识点应该按照难度递增、循序渐进的原则排列
3. 考虑知识点之间的先修关系和依赖关系
4. 将{duration_weeks}周划分为合理的教学阶段，每个阶段包含相关的知识点
5. 每个阶段应该有相应的实践作业来巩固学习

请按照以下JSON格式返回结果：
{{
    "course_name": "{course_name}",
    "subject": "{subject}",
    "duration_weeks": {duration_weeks},
    "description": "课程总体描述",
    "learning_objectives": ["总体学习目标1", "总体学习目标2", ...],
    "knowledge_points": [
        {{
            "id": "kp_1",
            "name": "知识点名称",
            "description": "知识点详细描述",
            "difficulty_level": 1,
            "prerequisites": ["前置知识点ID"],
            "learning_objectives": ["具体学习目标"],
            "key_concepts": ["核心概念"],
            "estimated_hours": 4
        }}
    ],
    "teaching_stages": [
        {{
            "stage_id": "stage_1",
            "name": "阶段名称",
            "week_start": 1,
            "week_end": 4,
            "description": "阶段描述",
            "knowledge_point_ids": ["kp_1", "kp_2"],
            "stage_objectives": ["阶段目标"],
            "assessment_focus": "评估重点"
        }}
    ]
}}

请确保返回的是有效的JSON格式，不要包含任何其他文本。"""

        response = self.client.chat.completions.create(
            model=Config.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "你是一名资深的教育专家和课程设计师。请严格按照要求返回JSON格式的结果，不要包含任何解释文字。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        content = response.choices[0].message.content
        # 清理响应内容，移除markdown标记
        cleaned_content = self._clean_json_response(content)
        course_data = json.loads(cleaned_content)
        return self._create_course_from_data(course_data)
    
    def _create_course_from_data(self, course_data: Dict[str, Any]) -> 'Course':
        """从数据创建课程对象"""
        from models.data_models import Course, KnowledgePoint, TeachingStage
        
        # 创建知识点对象
        knowledge_points = []
        for kp_data in course_data["knowledge_points"]:
            # 验证和修正数据
            difficulty_level = min(5, max(1, kp_data.get("difficulty_level", 1)))
            estimated_hours = min(20, max(1, kp_data.get("estimated_hours", 4)))
            
            knowledge_point = KnowledgePoint(
                id=kp_data["id"],
                name=kp_data["name"],
                description=kp_data["description"],
                difficulty_level=difficulty_level,
                prerequisites=kp_data.get("prerequisites", []),
                learning_objectives=kp_data.get("learning_objectives", []),
                key_concepts=kp_data.get("key_concepts", []),
                estimated_hours=estimated_hours
            )
            knowledge_points.append(knowledge_point)
        
        # 创建教学阶段对象
        teaching_stages = []
        for stage_data in course_data["teaching_stages"]:
            # 验证和修正数据
            week_start = max(1, stage_data.get("week_start", 1))
            week_end = min(course_data["duration_weeks"], max(week_start, stage_data.get("week_end", week_start + 1)))
            
            teaching_stage = TeachingStage(
                stage_id=stage_data["stage_id"],
                name=stage_data["name"],
                week_start=week_start,
                week_end=week_end,
                description=stage_data["description"],
                knowledge_point_ids=stage_data.get("knowledge_point_ids", []),
                stage_objectives=stage_data.get("stage_objectives", []),
                assessment_focus=stage_data.get("assessment_focus", "基础掌握")
            )
            teaching_stages.append(teaching_stage)
        
        # 创建课程对象
        course = Course(
            id=f"course_{course_data['course_name'].replace(' ', '_').lower()}",
            name=course_data["course_name"],
            subject=course_data["subject"],
            description=course_data["description"],
            duration_weeks=course_data["duration_weeks"],
            learning_objectives=course_data["learning_objectives"],
            knowledge_points=knowledge_points,
            teaching_stages=teaching_stages
        )
        
        return course
    
    def create_stage_assignment(self, course: 'Course', stage: 'TeachingStage') -> Assignment:
        """为特定教学阶段创建作业"""
        print(f"正在为阶段 '{stage.name}' 创建作业...")
        
        # 获取该阶段相关的知识点
        stage_knowledge_points = [
            kp for kp in course.knowledge_points 
            if kp.id in stage.knowledge_point_ids
        ]
        
        # 获取该阶段相关的知识点ID列表
        stage_kp_ids_json = json.dumps(stage.knowledge_point_ids)
        
        # 构建作业生成提示词
        prompt = f"""作为{course.subject}课程"{course.name}"的教师，请为教学阶段"{stage.name}"创建一个综合性实践作业。

阶段信息：
- 阶段时间：第{stage.week_start}-{stage.week_end}周
- 阶段描述：{stage.description}
- 评估重点：{stage.assessment_focus}

本阶段涉及的知识点：
{chr(10).join([f"- {kp.name}: {kp.description}" for kp in stage_knowledge_points])}

学习目标：
{chr(10).join([f"- {obj}" for obj in stage.stage_objectives])}

请设计一个适合的作业，要求：
1. 充分体现本阶段的知识点
2. 难度适中，符合循序渐进的原则
3. 具有实践性，能让学生巩固理论学习
4. 适合同伴互评
5. 明确的评价标准

请按照以下JSON格式返回：
{{
    "title": "作业标题",
    "description": "作业详细描述",
    "assignment_type": "programming|project|design_doc|research_report",
    "difficulty_level": 1-5,
    "requirements": ["具体要求1", "具体要求2", ...],
    "evaluation_criteria": {{
        "functionality": "功能实现评价标准",
        "code_quality": "代码质量评价标准", 
        "innovation": "创新性评价标准",
        "documentation": "文档完整性评价标准"
    }},
    "knowledge_points_covered": {stage_kp_ids_json},
    "estimated_hours": 预估完成时间,
    "deliverables": ["交付物1", "交付物2", ...]
}}

请确保返回有效的JSON格式。"""

        response = self.client.chat.completions.create(
            model=Config.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "你是一名优秀的教师，专门设计高质量的实践作业。请严格按照JSON格式返回结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        
        content = response.choices[0].message.content
        # 清理响应内容，移除markdown标记
        cleaned_content = self._clean_json_response(content)
        assignment_data = json.loads(cleaned_content)
        return self._create_assignment_from_data(assignment_data, course, stage)
    
    def _create_assignment_from_data(self, assignment_data: Dict[str, Any], 
                                   course: 'Course', stage: 'TeachingStage') -> Assignment:
        """从数据创建作业对象"""
        from models.data_models import Assignment, AssignmentType
        from utils.knowledge_point_resolver import KnowledgePointResolver
        import uuid
        
        # 映射作业类型
        type_mapping = {
            "programming": AssignmentType.PROGRAMMING,
            "project": AssignmentType.PROJECT,
            "design_doc": AssignmentType.DESIGN_DOC,
            "research_report": AssignmentType.RESEARCH_REPORT
        }
        
        # 验证和修正数据
        difficulty_level = min(5, max(1, assignment_data.get("difficulty_level", 2)))
        estimated_hours = min(40, max(2, assignment_data.get("estimated_hours", 8)))
        
        # 🔧 标准化知识点ID：将LLM返回的名称或ID统一转换为标准ID格式
        raw_kp_list = assignment_data.get("knowledge_points_covered", [])
        normalized_kp_list = self._normalize_knowledge_points(raw_kp_list, course)
        
        assignment = Assignment(
            id=f"assignment_{uuid.uuid4().hex[:8]}",
            title=assignment_data["title"],
            description=assignment_data["description"],
            assignment_type=type_mapping.get(assignment_data.get("assignment_type", "programming"), AssignmentType.PROGRAMMING),
            subject=course.subject,
            difficulty_level=difficulty_level,
            requirements=assignment_data.get("requirements", []),
            evaluation_criteria=assignment_data.get("evaluation_criteria", {}),
            max_score=100,
            course_id=course.id,
            stage_id=stage.stage_id,
            knowledge_points_covered=normalized_kp_list,
            estimated_hours=estimated_hours,
            deliverables=assignment_data.get("deliverables", [])
        )
        
        return assignment
    
    def adapt_assignment_for_student_level(self, assignment: Assignment, 
                                         student_performance_history: List[Dict]) -> Dict[str, Any]:
        """根据学生历史表现调整作业难度或提示"""
        if not student_performance_history:
            return {"hints": [], "difficulty_adjustment": 0}
        
        # 分析学生历史表现
        avg_score = sum(record["score"] for record in student_performance_history) / len(student_performance_history)
        recent_trend = self._analyze_performance_trend(student_performance_history[-3:])
        
        hints = []
        difficulty_adjustment = 0
        
        # 根据表现提供个性化支持
        if avg_score < 60:  # 学习困难的学生
            hints = [
                f"建议先复习相关知识点：{', '.join(assignment.knowledge_points_covered[:2])}",
                "可以参考课程资料中的示例代码",
                "遇到困难时及时向同学或老师求助"
            ]
            difficulty_adjustment = -1
        elif avg_score > 85:  # 优秀学生
            hints = [
                "尝试在基本要求基础上加入创新元素",
                "可以考虑优化算法性能或用户体验",
                "思考如何让代码更加优雅和可维护"
            ]
            difficulty_adjustment = 1
        elif recent_trend == "improving":  # 进步明显的学生
            hints = [
                "继续保持学习的节奏，你正在稳步进步",
                "可以尝试挑战稍微难一点的要求"
            ]
        
        return {
            "hints": hints,
            "difficulty_adjustment": difficulty_adjustment,
            "personalized_requirements": self._generate_personalized_requirements(assignment, avg_score)
        }
    
    def _analyze_performance_trend(self, recent_records: List[Dict]) -> str:
        """分析最近的表现趋势"""
        if len(recent_records) < 2:
            return "stable"
        
        scores = [record["score"] for record in recent_records]
        if scores[-1] > scores[0] + 10:
            return "improving"
        elif scores[-1] < scores[0] - 10:
            return "declining"
        else:
            return "stable"
    
    def _generate_personalized_requirements(self, assignment: Assignment, avg_score: float) -> List[str]:
        """为学生生成个性化要求"""
        base_requirements = assignment.requirements.copy()
        
        if avg_score < 60:
            # 简化要求，提供更多指导
            personalized = [
                "完成基本功能即可，重点关注正确性",
                "代码要有清晰的注释说明思路",
                "提交时包含遇到的问题和解决方法"
            ]
        elif avg_score > 85:
            # 提出更高要求
            personalized = base_requirements + [
                "考虑代码的可扩展性和复用性",
                "尝试使用设计模式优化代码结构",
                "提供性能分析和优化建议"
            ]
        else:
            personalized = base_requirements
        
        return personalized
    
    def _normalize_knowledge_points(self, kp_list: List[str], course: 'Course') -> List[str]:
        """标准化知识点列表
        
        将LLM返回的知识点名称或ID统一转换为标准ID格式
        
        Args:
            kp_list: 知识点列表（可能是名称或ID）
            course: 课程对象
            
        Returns:
            标准化后的知识点ID列表
        """
        from utils.knowledge_point_resolver import KnowledgePointResolver
        
        resolver = KnowledgePointResolver(course)
        standardized = []
        
        for kp in kp_list:
            # 如果已经是有效的ID，直接使用
            if resolver.is_valid_id(kp):
                standardized.append(kp)
            else:
                # 尝试从名称获取ID
                kp_id = resolver.get_id_by_name(kp)
                if kp_id:
                    standardized.append(kp_id)
                else:
                    # 如果既不是有效ID也找不到名称，保持原值
                    # （这样可以在后续处理中发现问题）
                    standardized.append(kp)
        
        return standardized
    
    def _clean_json_response(self, content: str) -> str:
        """清理API响应，提取JSON部分"""
        content = content.strip()
        
        # 移除markdown代码块标记
        if content.startswith('```json'):
            content = content[7:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        content = content.strip()
        
        # 尝试找到JSON开始和结束
        start_idx = content.find('{')
        end_idx = content.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            content = content[start_idx:end_idx+1]
        
        return content
    
    # ==================== 新增：学生分析功能 ====================
    
    def analyze_students_after_round(
        self,
        students: List[Any],  # List[StudentAgent]
        round_id: str,
        assignments: Dict[str, Any],  # student_id -> StudentWork
        evaluations_given: Dict[str, List[Dict]],  # student_id -> evaluations
        evaluations_received: Dict[str, List[Dict]]  # student_id -> evaluations
    ) -> Dict[str, Any]:
        """每轮互评后分析所有学生"""
        logging.info(f"开始分析第 {round_id} 轮的学生表现")
        
        analysis_results = {}
        
        for student_agent in students:
            student_id = student_agent.student.id
            
            # 获取该学生的作业和评价
            student_work = assignments.get(student_id)
            if not student_work:
                logging.warning(f"学生 {student_id} 没有作业记录")
                continue
            
            evals_given = evaluations_given.get(student_id, [])
            evals_received = evaluations_received.get(student_id, [])
            
            # 使用分析器分析
            try:
                analysis = self.analyzer.analyze_after_round(
                    student_id=student_id,
                    round_id=round_id,
                    student_work=student_work,
                    evaluations_given=evals_given,
                    evaluations_received=evals_received,
                    previous_knowledge_state=student_agent.student.knowledge_mastery.copy()
                )
                
                analysis_results[student_id] = analysis
                
                # 添加教师反馈到学生记忆系统
                if hasattr(student_agent, 'use_new_memory') and student_agent.use_new_memory:
                    self._add_teacher_feedback_to_student(
                        student_agent, round_id, analysis
                    )
                
                # 更新学生知识状态（合并而不是覆盖）
                for kp, mastery in analysis.knowledge_state.knowledge_mastery.items():
                    student_agent.student.knowledge_mastery[kp] = mastery
                
                # 将完整的知识状态更新回分析结果（用于报告生成）
                analysis.knowledge_state.knowledge_mastery = dict(student_agent.student.knowledge_mastery)
                
                logging.info(f"完成学生 {student_id} 的分析")
                
            except Exception as e:
                logging.error(f"分析学生 {student_id} 失败: {e}")
                continue
        
        logging.info(f"第 {round_id} 轮分析完成，共分析 {len(analysis_results)} 名学生")
        return analysis_results
    
    def _add_teacher_feedback_to_student(
        self,
        student_agent: Any,
        round_id: str,
        analysis: Any
    ):
        """将教师反馈添加到学生记忆系统"""
        try:
            feedback_memory = TeacherFeedbackMemory(
                id=f"mem_teacher_{round_id}_{student_agent.student.id}_{uuid.uuid4().hex[:8]}",
                content=f"第{round_id}轮教师反馈和分析",
                round_id=round_id,
                knowledge_state=analysis.knowledge_state.knowledge_mastery,
                knowledge_growth=analysis.knowledge_state.knowledge_growth,
                metacognition_level=analysis.metacognition.overall_score,
                evaluation_quality={
                    "depth": analysis.evaluation_quality.depth,
                    "accuracy": analysis.evaluation_quality.accuracy,
                    "constructiveness": analysis.evaluation_quality.constructiveness
                },
                feedback_content=analysis.feedback_to_student,
                strengths=analysis.knowledge_state.strengths,
                weaknesses=analysis.knowledge_state.weaknesses,
                recommendations=analysis.action_items,
                importance=0.9  # 教师反馈重要性高
            )
            
            student_agent.new_memory_system.add_memory(feedback_memory)
            logging.info(f"教师反馈已添加到学生 {student_agent.student.id} 的记忆系统")
            
        except Exception as e:
            logging.error(f"添加教师反馈失败: {e}")
    
    def generate_stage_reports(
        self,
        students: List[Any],
        stage_id: str,
        stage_name: str,
        start_round: int,
        end_round: int
    ) -> Dict[str, Any]:
        """生成阶段学情报告"""
        logging.info(f"开始生成 {stage_name} 阶段的学情报告")
        
        reports = {}
        
        for student_agent in students:
            try:
                report = self.analyzer.generate_stage_report(
                    student_id=student_agent.student.id,
                    stage_id=stage_id,
                    stage_name=stage_name,
                    start_round=start_round,
                    end_round=end_round,
                    student=student_agent.student  # 传递学生对象以获取完整信息
                )
                
                reports[student_agent.student.id] = report
                
                # 可选：将报告也添加到学生记忆
                if hasattr(student_agent, 'use_new_memory') and student_agent.use_new_memory:
                    self._add_stage_report_to_student(
                        student_agent, stage_id, report
                    )
                
                logging.info(f"完成学生 {student_agent.student.id} 的阶段报告")
                
            except Exception as e:
                logging.error(f"生成学生 {student_agent.student.id} 的报告失败: {e}")
                continue
        
        logging.info(f"阶段报告生成完成，共 {len(reports)} 份")
        return reports
    
    def _add_stage_report_to_student(
        self,
        student_agent: Any,
        stage_id: str,
        report: Any
    ):
        """将阶段报告添加到学生记忆"""
        try:
            report_memory = TeacherFeedbackMemory(
                id=f"mem_stage_report_{stage_id}_{student_agent.student.id}_{uuid.uuid4().hex[:8]}",
                content=f"{report.stage_name}阶段学情报告",
                round_id=f"stage_{stage_id}",
                stage_id=stage_id,
                knowledge_state=report.final_knowledge_mastery,
                knowledge_growth=report.knowledge_growth_rate,
                metacognition_level=report.metacognition_trajectory[-1][1] if report.metacognition_trajectory else 0.5,
                evaluation_quality={
                    "overall": report.avg_evaluation_quality_given
                },
                feedback_content=report.detailed_feedback,
                strengths=report.strengths,
                weaknesses=report.weaknesses,
                recommendations=report.next_stage_focus,
                is_stage_report=True,
                stage_summary=f"整体表现：{report.overall_performance}",
                importance=1.0  # 阶段报告非常重要
            )
            
            student_agent.new_memory_system.add_memory(report_memory)
            logging.info(f"阶段报告已添加到学生 {student_agent.student.id} 的记忆系统")
            
        except Exception as e:
            logging.error(f"添加阶段报告失败: {e}")
