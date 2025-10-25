import uuid
import random
from typing import List, Dict, Any
import openai
from models.data_models import Assignment, AssignmentType
from config.settings import Config

class AssignmentGenerator:
    """作业生成器"""
    
    def __init__(self):
        self.client = openai.OpenAI(
            api_key=Config.OPENAI_API_KEY,
            base_url=Config.OPENAI_BASE_URL
        )
        
        # 预定义的课程和主题
        self.subjects = {
            "数据结构与算法": ["排序算法", "树结构", "图算法", "动态规划", "哈希表"],
            "软件工程": ["需求分析", "系统设计", "测试用例", "项目管理", "代码重构"],
            "数据库系统": ["SQL查询", "数据库设计", "索引优化", "事务处理", "数据备份"],
            "计算机网络": ["网络协议", "路由算法", "网络安全", "Web开发", "分布式系统"],
            "人工智能": ["机器学习", "深度学习", "自然语言处理", "计算机视觉", "推荐系统"],
            "操作系统": ["进程管理", "内存管理", "文件系统", "并发控制", "系统调用"],
            "Web开发": ["前端框架", "后端API", "数据库集成", "用户认证", "响应式设计"]
        }
    
    def generate_assignments(self, count: int) -> List[Assignment]:
        """生成指定数量的作业"""
        assignments = []
        
        for _ in range(count):
            assignment = self._generate_single_assignment()
            assignments.append(assignment)
        
        return assignments
    
    def _generate_single_assignment(self) -> Assignment:
        """生成单个作业"""
        # 随机选择课程和主题
        subject = random.choice(list(self.subjects.keys()))
        topic = random.choice(self.subjects[subject])
        
        # 随机选择作业类型
        assignment_type = random.choice(list(AssignmentType))
        
        # 随机选择难度等级
        difficulty = random.randint(1, 5)
        
        # 使用LLM生成作业详情
        assignment_details = self._generate_assignment_details(
            subject, topic, assignment_type, difficulty
        )
        
        return Assignment(
            id=str(uuid.uuid4()),
            title=assignment_details["title"],
            description=assignment_details["description"],
            assignment_type=assignment_type,
            subject=subject,
            difficulty_level=difficulty,
            requirements=assignment_details["requirements"],
            evaluation_criteria=assignment_details["evaluation_criteria"],
            max_score=100
        )
    
    def _generate_assignment_details(self, subject: str, topic: str, 
                                   assignment_type: AssignmentType, 
                                   difficulty: int) -> Dict[str, Any]:
        """使用LLM生成作业详细内容"""
        
        prompt = f"""请为高校计算机专业课程生成一个作业。

课程：{subject}
主题：{topic}
作业类型：{assignment_type.value}
难度等级：{difficulty}/5 (1=入门，5=高级)

请按以下格式输出：

=== 标题 ===
[简洁明确的作业标题]

=== 描述 ===
[详细的作业描述，包括背景和目标]

=== 要求 ===
1. [具体要求1]
2. [具体要求2]
3. [具体要求3]
...

=== 评价标准 ===
功能实现: [对功能实现的评价标准]
代码质量: [对代码质量的评价标准]
创新性: [对创新性的评价标准]
文档完整性: [对文档的评价标准]

请确保作业内容符合难度等级，并且有一定的实践性和教育意义。
"""
        
        response = self.client.chat.completions.create(
            model=Config.DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": "你是一位经验丰富的计算机专业教师，擅长设计有教育价值的编程作业。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )
        
        content = response.choices[0].message.content
        return self._parse_assignment_response(content)
    
    def _parse_assignment_response(self, content: str) -> Dict[str, Any]:
        """解析LLM生成的作业内容"""
        sections = {}
        current_section = None
        current_content = []
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('=== ') and line.endswith(' ==='):
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()
                current_section = line[4:-4]
                current_content = []
            else:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()
        
        # 解析要求列表
        requirements = []
        if "要求" in sections:
            req_lines = sections["要求"].split('\n')
            for line in req_lines:
                line = line.strip()
                if line and (line.startswith(tuple("123456789")) or line.startswith('- ')):
                    # 去掉序号前缀
                    clean_req = line.split('.', 1)[-1].strip() if '.' in line else line.strip('- ')
                    requirements.append(clean_req)
        
        # 解析评价标准
        evaluation_criteria = {}
        if "评价标准" in sections:
            criteria_lines = sections["评价标准"].split('\n')
            for line in criteria_lines:
                if ':' in line or '：' in line:
                    parts = line.split(':' if ':' in line else '：', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        evaluation_criteria[key] = value
        
        return {
            "title": sections.get("标题", "编程作业"),
            "description": sections.get("描述", "请完成指定的编程任务"),
            "requirements": requirements if requirements else ["实现基本功能", "编写清晰的代码", "提供必要的文档"],
            "evaluation_criteria": evaluation_criteria if evaluation_criteria else {
                "功能实现": "能否正确实现所需功能",
                "代码质量": "代码结构、命名、注释等质量",
                "创新性": "解决方案的创新程度",
                "文档完整性": "文档的完整性和清晰度"
            }
        }
