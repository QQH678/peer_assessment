import uuid
import json
import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from models.data_models import (SemesterSimulation, Course, Student, Assignment, 
                               StudentWork, PeerEvaluation, safe_to_dict)
from agents.teachers.teacher_agent import TeacherAgent
from agents.students.student_generator import StudentGenerator
from agents.students.student_agent import StudentAgent
from agents.evaluators.evaluator_agent import EvaluatorAgent
from config.settings import Config
from config.peer_review_config import PeerReviewConfig

class SemesterSimulator:
    """学期教学模拟器"""
    
    def __init__(self, use_new_memory: bool = True, peer_config: Optional[PeerReviewConfig] = None):
        """
        初始化学期模拟器
        
        Args:
            use_new_memory: 是否使用新的三维记忆系统
            peer_config: 互评配置，如果为None则使用默认配置
        """
        self.use_new_memory = use_new_memory
        self.peer_config = peer_config or PeerReviewConfig()
        self.teacher_agent = TeacherAgent(config=self.peer_config)
        self.student_generator = StudentGenerator()
        Config.ensure_directories()
        
        logging.info(f"学期模拟器初始化: 新记忆系统={use_new_memory}, 每阶段{self.peer_config.rounds_per_stage}轮")
    
    def run_semester_simulation(self, 
                              course_name: str,
                              subject: str,
                              student_count: int = 30,
                              duration_weeks: int = 16,
                              evaluations_per_assignment: int = 3) -> SemesterSimulation:
        """运行完整的学期教学模拟"""
        
        print(f"=== 开始学期教学模拟 ===")
        print(f"课程：{course_name} ({subject})")
        print(f"学生数量：{student_count}")
        print(f"课程周数：{duration_weeks}")
        
        # 1. 教师设计课程
        print("\n1. 教师设计课程体系...")
        course = self.teacher_agent.design_course(course_name, subject, duration_weeks)
        print(f"   - 共设计 {len(course.knowledge_points)} 个知识点")
        print(f"   - 划分为 {len(course.teaching_stages)} 个教学阶段")
        
        # 2. 生成学生
        print("\n2. 生成学生群体...")
        students = self.student_generator.generate_students(student_count)
        
        # 为学生初始化基础知识
        self._initialize_student_knowledge(students, course)
        
        # 3. 创建学期模拟对象
        semester = SemesterSimulation(
            id=f"semester_{uuid.uuid4().hex[:8]}",
            course=course,
            students=students
        )
        
        # 4. 创建学生Agent（整个学期复用，保持记忆连续性）
        print(f"\n3. 初始化学生智能代理...")
        student_agents_map = {}  # {student_id: StudentAgent}
        for student in students:
            memory_config = {
                "use_new_memory": self.use_new_memory,
                "use_semantic_retrieval": True,
                "enable_experience_replay": True,
                "enable_quality_control": True
            }
            agent = StudentAgent(
                student=student,
                memory_config=memory_config,
                peer_review_config=self.peer_config
            )
            student_agents_map[student.id] = agent
        print(f"   ✓ 创建{len(student_agents_map)}个学生代理")
        
        # 5. 逐阶段进行教学模拟
        print(f"\n4. 开始分阶段教学模拟...")
        stage_count = 0
        
        while semester.advance_to_next_stage() is not None:
            stage_count += 1
            current_stage = semester.current_stage
            print(f"\n=== 阶段 {stage_count}: {current_stage.name} ===")
            print(f"   周次：第{current_stage.week_start}-{current_stage.week_end}周")
            print(f"   涉及知识点：{len(current_stage.knowledge_point_ids)}个")
            
            # 教师为当前阶段创建作业
            assignment = self.teacher_agent.create_stage_assignment(course, current_stage)
            semester.assignments.append(assignment)
            print(f"   创建作业：{assignment.title}")
            
            # 模拟学习过程（学生掌握知识点）
            self._simulate_learning_process(semester, current_stage)
            
            # 学生完成作业（使用已创建的agents）
            print("   学生完成作业...")
            stage_works = self._simulate_assignment_completion_with_existing_agents(
                semester, assignment, course, student_agents_map
            )
            semester.works.extend(stage_works)
            
            # 进行多轮互评（根据配置的rounds_per_stage）
            print(f"   进行{self.peer_config.rounds_per_stage}轮同伴互评...")
            stage_evaluations = []
            
            for round_num in range(1, self.peer_config.rounds_per_stage + 1):
                print(f"   → 第{round_num}轮互评...")
                
                # 本轮互评
                round_evaluations = self._simulate_peer_evaluation_round(
                    semester, stage_works, assignment, 
                    student_agents_map, round_num
                )
                stage_evaluations.extend(round_evaluations)
                semester.evaluations.extend(round_evaluations)
                
                # 教师每轮分析
                if self.use_new_memory and round_num < self.peer_config.rounds_per_stage:
                    print(f"   → 教师进行第{round_num}轮学习分析...")
                    try:
                        # 准备分析所需的数据
                        # 创建增强的作品对象（添加assignment引用）
                        class WorkWithAssignment:
                            """带assignment引用的StudentWork包装器"""
                            def __init__(self, work: StudentWork, assignment: Assignment):
                                object.__setattr__(self, '_work_dict', work.dict())
                                object.__setattr__(self, 'assignment', assignment)
                                
                            def __getattr__(self, name):
                                # 当访问不存在的属性时，从_work_dict获取
                                _work_dict = object.__getattribute__(self, '_work_dict')
                                if name in _work_dict:
                                    return _work_dict[name]
                                raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
                        
                        assignments_map = {}
                        for work in stage_works:
                            work_with_assignment = WorkWithAssignment(work, assignment)
                            assignments_map[work.student_id] = work_with_assignment
                            
                            # 调试：验证包装器是否正常
                            try:
                                _ = work_with_assignment.content
                                _ = work_with_assignment.assignment
                            except Exception as e:
                                print(f"   警告：WorkWithAssignment包装器异常: {e}")
                                logging.error(f"WorkWithAssignment包装器异常: {e}")
                        
                        # 按学生整理互评数据
                        evaluations_given = {}
                        evaluations_received = {}
                        for eval_obj in round_evaluations:
                            # 评价者给出的互评
                            if eval_obj.evaluator_id not in evaluations_given:
                                evaluations_given[eval_obj.evaluator_id] = []
                            evaluations_given[eval_obj.evaluator_id].append(eval_obj.to_dict())
                            
                            # 作者收到的互评
                            work = next((w for w in stage_works if w.id == eval_obj.work_id), None)
                            if work:
                                if work.student_id not in evaluations_received:
                                    evaluations_received[work.student_id] = []
                                evaluations_received[work.student_id].append(eval_obj.to_dict())
                        
                        analyses = self.teacher_agent.analyze_students_after_round(
                            students=list(student_agents_map.values()),
                            round_id=f"stage{stage_count}_round{round_num}",
                            assignments=assignments_map,
                            evaluations_given=evaluations_given,
                            evaluations_received=evaluations_received
                        )
                        print(f"      ✓ 完成{len(analyses)}个学生的分析")
                    except Exception as e:
                        logging.warning(f"教师分析失败: {e}")
                
                # 学生推进到下一轮（触发记忆巩固）
                if self.use_new_memory:
                    print(f"   → 学生推进到下一轮（轮{round_num}）...")
                    for agent in student_agents_map.values():
                        try:
                            agent.advance_round()
                        except Exception as e:
                            logging.warning(f"学生 {agent.student.name} 推进轮次失败: {e}")
            
            # 阶段结束后生成学情报告
            if self.use_new_memory:
                print(f"   → 教师生成阶段{stage_count}学情报告...")
                try:
                    reports = self.teacher_agent.generate_stage_reports(
                        students=list(student_agents_map.values()),
                        stage_id=f"stage_{stage_count}",
                        stage_name=current_stage.name,
                        start_round=1,
                        end_round=self.peer_config.rounds_per_stage
                    )
                    # 保存报告到文件
                    self._save_stage_reports(semester.id, stage_count, reports)
                    
                    # 保存报告以便后续生成综合报告
                    semester.all_stage_reports[f"stage_{stage_count}"] = reports
                    
                    print(f"      ✓ 生成{len(reports)}份学情报告")
                except Exception as e:
                    logging.warning(f"学情报告生成失败: {e}")
            
            print(f"   阶段完成：{len(stage_works)}个作品，{len(stage_evaluations)}次互评")
        
        # 6. 保存所有学生的记忆状态（使用新记忆系统）
        if self.use_new_memory:
            print(f"\n5. 保存学生记忆状态...")
            self._save_student_memories(semester, student_agents_map)
        
        # 7. 生成学期综合报告（新增）
        print(f"\n6. 生成学生综合学情报告...")
        try:
            comprehensive_reports = self.teacher_agent.generate_comprehensive_student_reports(
                semester=semester,
                stage_reports_dict=semester.all_stage_reports,
                output_dir=None,  # 使用默认目录
                use_v0_api=False  # 默认不调用V0 API，仅生成prompt
            )
            print(f"   ✓ 已生成{len(comprehensive_reports.get('reports', {}))}份综合学情报告")
        except Exception as e:
            logging.error(f"生成综合报告失败: {e}")
            import traceback
            logging.error(traceback.format_exc())
        
        # 8. 保存模拟结果
        self._save_semester_simulation(semester)
        
        print(f"\n=== 学期模拟完成 ===")
        print(f"总计：{len(semester.assignments)}个作业，{len(semester.works)}个作品，{len(semester.evaluations)}次互评")
        
        return semester
    
    def _initialize_student_knowledge(self, students: List[Student], course: Course):
        """为学生初始化基础知识"""
        print("   初始化学生基础知识...")
        
        for student in students:
            # 根据学生类型和专业背景初始化知识
            base_knowledge_level = {
                "excellent": 0.6,
                "good": 0.4,
                "average": 0.2,
                "below_average": 0.1,
                "strict": 0.3,
                "lenient": 0.3
            }.get(student.student_type.value, 0.2)
            
            # 为基础知识点设置初始掌握程度
            basic_knowledge_points = [kp for kp in course.knowledge_points if kp.difficulty_level <= 2]
            for kp in basic_knowledge_points:
                mastery_level = base_knowledge_level * (1.0 - 0.1 * (kp.difficulty_level - 1))
                if mastery_level > 0.5:  # 达到基础掌握
                    student.update_long_term_memory(kp.id, {
                        "concepts": kp.key_concepts,
                        "source": "prior_knowledge"
                    })
                    student.knowledge_mastery[kp.id] = mastery_level
                else:  # 只有模糊记忆
                    student.update_short_term_memory(kp.id, {
                        "concepts": kp.key_concepts[:1],  # 只记得部分概念
                        "source": "prior_exposure"
                    })
    
    def _simulate_learning_process(self, semester: SemesterSimulation, stage: 'TeachingStage'):
        """模拟学习过程"""
        # 模拟学生在该阶段学习新知识点
        for student in semester.students:
            for kp_id in stage.knowledge_point_ids:
                kp = semester.course.get_knowledge_point_by_id(kp_id)
                if kp:
                    # 学习效果取决于学生能力和前置知识掌握情况
                    learning_effectiveness = self._calculate_learning_effectiveness(
                        student, kp, semester.course
                    )
                    
                    # 更新短期记忆
                    student.update_short_term_memory(kp_id, {
                        "concepts": kp.key_concepts,
                        "learning_stage": stage.name,
                        "effectiveness": learning_effectiveness
                    })
                    
                    # 根据学习效果更新掌握程度
                    current_mastery = student.knowledge_mastery.get(kp_id, 0.0)
                    mastery_gain = 0.3 * learning_effectiveness
                    new_mastery = min(1.0, current_mastery + mastery_gain)
                    student.knowledge_mastery[kp_id] = new_mastery
    
    def _calculate_learning_effectiveness(self, student: Student, kp: 'KnowledgePoint', course: Course) -> float:
        """计算学习效果"""
        base_effectiveness = {
            "excellent": 0.9,
            "good": 0.75,
            "average": 0.6,
            "below_average": 0.4,
            "strict": 0.7,
            "lenient": 0.65
        }.get(student.student_type.value, 0.6)
        
        # 检查前置知识掌握情况
        prereq_mastery = 1.0
        if kp.prerequisites:
            prereq_levels = [student.knowledge_mastery.get(prereq_id, 0.0) for prereq_id in kp.prerequisites]
            prereq_mastery = sum(prereq_levels) / len(prereq_levels) if prereq_levels else 1.0
        
        # 考虑难度影响
        difficulty_factor = max(0.3, 1.1 - 0.1 * kp.difficulty_level)
        
        return base_effectiveness * prereq_mastery * difficulty_factor
    
    def _simulate_assignment_completion(self, semester: SemesterSimulation, 
                                      assignment: Assignment, course: Course) -> List[StudentWork]:
        """模拟学生完成作业"""
        works = []
        
        for student in semester.students:
            try:
                # 创建记忆配置
                memory_config = {
                    "use_new_memory": self.use_new_memory,
                    "use_semantic_retrieval": True,
                    "enable_experience_replay": True,
                    "enable_quality_control": True
                }
                
                # 创建学生代理
                student_agent = StudentAgent(
                    student=student,
                    memory_config=memory_config,
                    peer_review_config=self.peer_config
                )
                
                # 如果使用旧记忆系统，加载记忆状态
                if not self.use_new_memory:
                    memory_path = f"data/memory_states"
                    os.makedirs(memory_path, exist_ok=True)
                    student_agent.load_memory_state(memory_path)
                
                # 完成作业
                work = student_agent.complete_assignment(assignment, course)
                works.append(work)
                
                # 如果使用旧记忆系统，保存记忆状态
                if not self.use_new_memory:
                    try:
                        student_agent.save_memory_state(memory_path)
                    except Exception as save_error:
                        logging.warning(f"学生 {student.name} 记忆保存失败: {save_error}")
                
            except json.JSONDecodeError as e:
                print(f"   警告：学生 {student.name} 作业完成失败 (JSON解析错误): {e}")
                logging.error(f"JSON解析错误 - 学生: {student.name}, 错误: {e}")
                continue
            except Exception as e:
                print(f"   警告：学生 {student.name} 作业完成失败: {e}")
                logging.error(f"作业完成失败 - 学生: {student.name}, 错误: {e}")
                continue
        
        return works
    
    def _simulate_assignment_completion_with_existing_agents(
        self, 
        semester: SemesterSimulation, 
        assignment: Assignment, 
        course: Course,
        student_agents: dict
    ) -> List[StudentWork]:
        """使用已有的StudentAgent完成作业（保持记忆连续性）"""
        works = []
        
        for student in semester.students:
            try:
                # 使用已有的StudentAgent
                student_agent = student_agents.get(student.id)
                if not student_agent:
                    logging.warning(f"学生 {student.name} 没有对应的Agent")
                    continue
                
                # 完成作业
                work = student_agent.complete_assignment(assignment, course)
                works.append(work)
                
            except json.JSONDecodeError as e:
                print(f"   警告：学生 {student.name} 作业完成失败 (JSON解析错误): {e}")
                logging.error(f"JSON解析错误 - 学生: {student.name}, 错误: {e}")
                continue
            except Exception as e:
                print(f"   警告：学生 {student.name} 作业完成失败: {e}")
                logging.error(f"作业完成失败 - 学生: {student.name}, 错误: {e}")
                continue
        
        return works
    
    def _simulate_assignment_completion_with_agents(self, semester: SemesterSimulation, 
                                      assignment: Assignment, course: Course) -> tuple[List[StudentWork], dict]:
        """模拟学生完成作业（返回作品和StudentAgent映射）- 已废弃，保留兼容性"""
        works = []
        student_agents = {}  # {student_id: StudentAgent}
        
        for student in semester.students:
            try:
                # 创建记忆配置
                memory_config = {
                    "use_new_memory": self.use_new_memory,
                    "use_semantic_retrieval": True,
                    "enable_experience_replay": True,
                    "enable_quality_control": True
                }
                
                # 创建学生代理
                student_agent = StudentAgent(
                    student=student,
                    memory_config=memory_config,
                    peer_review_config=self.peer_config
                )
                
                # 如果使用旧记忆系统，加载记忆状态
                if not self.use_new_memory:
                    memory_path = f"data/memory_states"
                    os.makedirs(memory_path, exist_ok=True)
                    student_agent.load_memory_state(memory_path)
                
                # 完成作业
                work = student_agent.complete_assignment(assignment, course)
                works.append(work)
                student_agents[student.id] = student_agent  # 保存引用
                
                # 如果使用旧记忆系统，保存记忆状态
                if not self.use_new_memory:
                    try:
                        student_agent.save_memory_state(memory_path)
                    except Exception as save_error:
                        logging.warning(f"学生 {student.name} 记忆保存失败: {save_error}")
                
            except json.JSONDecodeError as e:
                print(f"   警告：学生 {student.name} 作业完成失败 (JSON解析错误): {e}")
                logging.error(f"JSON解析错误 - 学生: {student.name}, 错误: {e}")
                continue
            except Exception as e:
                print(f"   警告：学生 {student.name} 作业完成失败: {e}")
                logging.error(f"作业完成失败 - 学生: {student.name}, 错误: {e}")
                continue
        
        return works, student_agents
    
    def _simulate_peer_evaluation_round(self, semester: SemesterSimulation, 
                                works: List[StudentWork], 
                                assignment: Assignment,
                                student_agents: dict,
                                round_number: int) -> List[PeerEvaluation]:
        """模拟一轮同伴互评（使用新记忆系统）"""
        evaluations = []
        
        # 根据配置分配互评对
        for work in works:
            # 找到作品作者的StudentAgent
            work_author_agent = student_agents.get(work.student_id)
            if not work_author_agent:
                print(f"   警告：找不到作品 {work.id} 的作者")
                continue
            
            # 为每个作品分配评价者
            evaluators = self._assign_evaluators(
                work, semester.students, self.peer_config.peers_per_round
            )
            
            for evaluator in evaluators:
                try:
                    evaluator_agent = student_agents.get(evaluator.id)
                    
                    if self.use_new_memory and evaluator_agent:
                        # 使用新记忆系统进行互评
                        evaluation_data = evaluator_agent.evaluate_peer_work(
                            peer_work=work,
                            assignment=assignment
                        )
                        
                        # 从评价数据中提取分数（旧格式返回的是简化版）
                        score = evaluation_data.get("score", 75)
                        
                        # 创建EvaluationScore对象（按比例分配）
                        from models.data_models import EvaluationScore
                        eval_score = EvaluationScore(
                            functionality=int(score * 0.4),
                            code_quality=int(score * 0.3),
                            innovation=int(score * 0.15),
                            documentation=int(score * 0.15)
                        )
                        
                        # 创建完整的PeerEvaluation对象
                        evaluation = PeerEvaluation(
                            id=f"eval_{uuid.uuid4().hex[:8]}",
                            evaluator_id=evaluator.id,
                            work_id=work.id,
                            assignment_id=assignment.id,
                            scores=eval_score,
                            comments={
                                "strengths": "\n".join(evaluation_data.get("strengths", [])),
                                "weaknesses": "\n".join(evaluation_data.get("weaknesses", [])),
                                "suggestions": "\n".join(evaluation_data.get("suggestions", []))
                            },
                            overall_comment=evaluation_data.get("content", ""),
                            evaluation_time=datetime.now(),
                            time_spent_minutes=round_number * 15  # 估算时间
                        )
                        
                        # 作者接收反馈
                        work_author_agent.receive_peer_evaluation(
                            evaluation_data={
                                "content": evaluation.overall_comment,
                                "score": evaluation.scores.get_weighted_score(
                                    {"functionality": 0.4, "code_quality": 0.3, 
                                     "innovation": 0.15, "documentation": 0.15}
                                ),
                                "strengths": evaluation.comments.get("strengths", "").split("\n"),
                                "weaknesses": evaluation.comments.get("weaknesses", "").split("\n"),
                                "suggestions": evaluation.comments.get("suggestions", "").split("\n")
                            },
                            evaluator_id=evaluator.id,
                            my_work=work,
                            assignment=assignment
                        )
                    else:
                        # 使用旧系统（EvaluatorAgent）
                        evaluator_agent_old = EvaluatorAgent(evaluator)
                        evaluation = evaluator_agent_old.evaluate_work(
                            work, assignment, work_author_agent.student
                        )
                    
                    evaluations.append(evaluation)
                    
                except Exception as e:
                    print(f"   警告：评价失败 (评价者: {evaluator.name}): {e}")
                    logging.error(f"互评失败 - 评价者: {evaluator.name}, 错误: {e}")
                    continue
        
        return evaluations
    
    def _save_stage_reports(self, semester_id: str, stage_number: int, reports: List[dict]):
        """保存阶段学情报告"""
        import os
        
        semester_dir = os.path.join(Config.DATA_DIR, f"semester_{semester_id}")
        os.makedirs(semester_dir, exist_ok=True)
        
        report_file = os.path.join(semester_dir, f"teacher_reports_stage_{stage_number}.json")
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(reports, f, ensure_ascii=False, indent=2, default=str)
            print(f"      报告已保存至: {report_file}")
        except Exception as e:
            logging.error(f"保存学情报告失败: {e}")
    
    def _save_student_memories(self, semester: SemesterSimulation, student_agents: dict):
        """保存所有学生的记忆状态到student对象中"""
        for student_id, agent in student_agents.items():
            try:
                # 找到对应的学生对象
                student = next((s for s in semester.students if s.id == student_id), None)
                if not student:
                    continue
                
                # 【新增】保存元认知调节器
                if hasattr(agent, 'metacognitive_regulator') and agent.metacognitive_regulator:
                    try:
                        agent.metacognitive_regulator.save()
                        logging.info(f"学生 {student.name} 的元认知调节器已保存")
                    except Exception as reg_error:
                        logging.warning(f"学生 {student.name} 的调节器保存失败: {reg_error}")
                
                # 从新记忆系统获取记忆数据
                if hasattr(agent, 'new_memory_system') and agent.new_memory_system:
                    # 使用正确的方法名：get_state() 返回 StudentMemoryState 对象
                    memory_state = agent.new_memory_system.get_state()
                    
                    # 将记忆转换为可序列化的格式
                    from memory.new_memory_models import MemoryDimension
                    stm_by_dimension = {
                        "learning_memories": [m.dict() for m in memory_state.short_term_memories 
                                             if m.dimension == MemoryDimension.LEARNING],
                        "peer_evaluation_memories": [m.dict() for m in memory_state.short_term_memories 
                                                    if m.dimension == MemoryDimension.PEER_EVALUATION],
                        "received_evaluation_memories": [m.dict() for m in memory_state.short_term_memories 
                                                        if m.dimension == MemoryDimension.RECEIVED_EVALUATION],
                        "teacher_feedback_memories": [m.dict() for m in memory_state.short_term_memories 
                                                     if m.dimension == MemoryDimension.TEACHER_FEEDBACK]
                    }
                    
                    # 更新学生对象的记忆
                    student.short_term_memory = stm_by_dimension
                    
                    # 长期记忆
                    ltm_by_dimension = {}
                    for mem in memory_state.long_term_memories:
                        dim = mem.dimension
                        if dim not in ltm_by_dimension:
                            ltm_by_dimension[dim] = []
                        ltm_by_dimension[dim].append(mem.dict())
                    
                    student.long_term_memory = ltm_by_dimension
                    
            except Exception as e:
                logging.warning(f"保存学生 {student_id} 记忆失败: {e}")
                import traceback
                logging.warning(traceback.format_exc())
    
    def _simulate_peer_evaluation(self, semester: SemesterSimulation, 
                                works: List[StudentWork], 
                                assignment: Assignment,
                                evaluations_per_work: int) -> List[PeerEvaluation]:
        """模拟同伴互评"""
        evaluations = []
        
        for work in works:
            # 找到作品作者
            work_author = None
            for student in semester.students:
                if student.id == work.student_id:
                    work_author = student
                    break
            
            if work_author is None:
                print(f"   警告：找不到作品 {work.id} 的作者")
                continue
            
            # 为每个作品分配评价者
            evaluators = self._assign_evaluators(work, semester.students, evaluations_per_work)
            
            for evaluator in evaluators:
                try:
                    evaluator_agent = EvaluatorAgent(evaluator)
                    evaluation = evaluator_agent.evaluate_work(work, assignment, work_author)
                    evaluations.append(evaluation)
                except Exception as e:
                    print(f"   警告：评价失败: {e}")
                    continue
        
        return evaluations
    
    def _assign_evaluators(self, work: StudentWork, all_students: List[Student], 
                          count: int) -> List[Student]:
        """为作品分配评价者"""
        import random
        
        # 排除作者本人
        available_evaluators = [s for s in all_students if s.id != work.student_id]
        
        # 随机选择评价者
        selected_count = min(count, len(available_evaluators))
        return random.sample(available_evaluators, selected_count)
    
    def _save_semester_simulation(self, semester: SemesterSimulation):
        """保存学期模拟结果"""
        import os
        
        # 创建保存目录
        semester_dir = os.path.join(Config.DATA_DIR, f"semester_{semester.id}")
        os.makedirs(semester_dir, exist_ok=True)
        
        # 保存课程信息
        with open(os.path.join(semester_dir, "course.json"), "w", encoding="utf-8") as f:
            json.dump(safe_to_dict(semester.course), f, ensure_ascii=False, indent=2, default=str)
        
        # 保存学生信息
        students_data = [student.to_dict() for student in semester.students]
        with open(os.path.join(semester_dir, "students.json"), "w", encoding="utf-8") as f:
            json.dump(students_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存作业信息
        assignments_data = [assignment.to_dict() for assignment in semester.assignments]
        with open(os.path.join(semester_dir, "assignments.json"), "w", encoding="utf-8") as f:
            json.dump(assignments_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存作品信息
        works_data = [work.to_dict() for work in semester.works]
        with open(os.path.join(semester_dir, "works.json"), "w", encoding="utf-8") as f:
            json.dump(works_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存评价信息
        evaluations_data = [eval.to_dict() for eval in semester.evaluations]
        with open(os.path.join(semester_dir, "evaluations.json"), "w", encoding="utf-8") as f:
            json.dump(evaluations_data, f, ensure_ascii=False, indent=2, default=str)
        
        # 保存统计信息
        statistics = self._generate_semester_statistics(semester)
        with open(os.path.join(semester_dir, "statistics.json"), "w", encoding="utf-8") as f:
            json.dump(statistics, f, ensure_ascii=False, indent=2, default=str)
        
        print(f"   模拟结果已保存至: {semester_dir}")
    
    def _generate_semester_statistics(self, semester: SemesterSimulation) -> Dict[str, Any]:
        """生成学期统计信息"""
        return {
            "semester_id": semester.id,
            "course_name": semester.course.name,
            "total_students": len(semester.students),
            "total_stages": len(semester.course.teaching_stages),
            "total_assignments": len(semester.assignments),
            "total_works": len(semester.works),
            "total_evaluations": len(semester.evaluations),
            "knowledge_points_covered": len(semester.course.knowledge_points),
            "student_type_distribution": self._get_student_type_distribution(semester.students),
            "assignment_difficulty_distribution": self._get_difficulty_distribution(semester.assignments),
            "completion_rate": len(semester.works) / (len(semester.students) * len(semester.assignments)) if semester.students and semester.assignments else 0
        }
    
    def _get_student_type_distribution(self, students: List[Student]) -> Dict[str, int]:
        """获取学生类型分布"""
        distribution = {}
        for student in students:
            student_type = student.student_type.value
            distribution[student_type] = distribution.get(student_type, 0) + 1
        return distribution
    
    def _get_difficulty_distribution(self, assignments: List[Assignment]) -> Dict[str, int]:
        """获取作业难度分布"""
        distribution = {}
        for assignment in assignments:
            difficulty = f"level_{assignment.difficulty_level}"
            distribution[difficulty] = distribution.get(difficulty, 0) + 1
        return distribution
