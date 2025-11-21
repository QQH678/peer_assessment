"""
课程模板配置
定义不同课程类型的评价维度
"""

from typing import Dict, List, Any

COURSE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    # ===== 编程类课程 =====
    "programming": {
        "name": "编程实践类",
        "name_en": "Programming",
        "subjects": [
            "数据结构与算法", "软件工程", "Web开发", "数据库系统",
            "计算机网络", "操作系统", "人工智能", "机器学习",
            "计算机科学", "软件开发"
        ],
        "evaluation_dimensions": [
            {
                "key": "functionality",
                "name": "功能实现",
                "name_en": "Functionality",
                "description": "是否满足需求，功能是否完整正确，能否正常运行"
            },
            {
                "key": "code_quality",
                "name": "代码质量",
                "name_en": "Code Quality",
                "description": "代码结构、可读性、规范性、注释完整性"
            },
            {
                "key": "innovation",
                "name": "创新性",
                "name_en": "Innovation",
                "description": "是否有创新思路或优化方案，算法效率"
            },
            {
                "key": "documentation",
                "name": "文档完整性",
                "name_en": "Documentation",
                "description": "文档是否清晰完整，包含使用说明和测试用例"
            }
        ]
    },
    
    # ===== 写作类课程 =====
    "writing": {
        "name": "写作表达类",
        "name_en": "Writing",
        "subjects": [
            "学术写作", "技术写作", "创意写作", "文献综述",
            "论文写作", "新闻写作", "商务写作"
        ],
        "evaluation_dimensions": [
            {
                "key": "content_quality",
                "name": "内容质量",
                "name_en": "Content Quality",
                "description": "论点是否清晰，论据是否充分，内容是否深入"
            },
            {
                "key": "structure",
                "name": "结构组织",
                "name_en": "Structure",
                "description": "文章结构是否合理，逻辑是否清晰，层次是否分明"
            },
            {
                "key": "language",
                "name": "语言表达",
                "name_en": "Language",
                "description": "语言是否准确、流畅、规范，表达是否清晰"
            },
            {
                "key": "originality",
                "name": "原创性",
                "name_en": "Originality",
                "description": "观点是否新颖，是否有独立思考和见解"
            }
        ]
    },
    
    # ===== 设计类课程 =====
    "design": {
        "name": "设计创作类",
        "name_en": "Design",
        "subjects": [
            "UI设计", "UX设计", "平面设计", "产品设计",
            "交互设计", "视觉设计", "工业设计"
        ],
        "evaluation_dimensions": [
            {
                "key": "aesthetics",
                "name": "美学质量",
                "name_en": "Aesthetics",
                "description": "视觉呈现是否美观，设计感是否强，配色是否协调"
            },
            {
                "key": "usability",
                "name": "可用性",
                "name_en": "Usability",
                "description": "是否易用，交互是否合理，用户体验是否良好"
            },
            {
                "key": "creativity",
                "name": "创意性",
                "name_en": "Creativity",
                "description": "设计理念是否创新，是否有独特性和亮点"
            },
            {
                "key": "completeness",
                "name": "完整性",
                "name_en": "Completeness",
                "description": "设计是否完整，细节是否到位，规范是否符合"
            }
        ]
    },
    
    # ===== 理论分析类课程 =====
    "theory": {
        "name": "理论分析类",
        "name_en": "Theory & Analysis",
        "subjects": [
            "经济学", "管理学", "社会学", "心理学",
            "哲学", "政治学", "法学", "教育学"
        ],
        "evaluation_dimensions": [
            {
                "key": "understanding",
                "name": "理解深度",
                "name_en": "Understanding",
                "description": "对理论的理解是否深入透彻，概念掌握是否准确"
            },
            {
                "key": "analysis",
                "name": "分析能力",
                "name_en": "Analysis",
                "description": "分析是否系统，逻辑是否严密，论证是否充分"
            },
            {
                "key": "critical_thinking",
                "name": "批判性思维",
                "name_en": "Critical Thinking",
                "description": "是否能批判性地思考问题，有独立见解"
            },
            {
                "key": "application",
                "name": "应用能力",
                "name_en": "Application",
                "description": "能否将理论应用于实际问题，举例是否恰当"
            }
        ]
    },
    
    # ===== 实验类课程 =====
    "experiment": {
        "name": "实验操作类",
        "name_en": "Experiment",
        "subjects": [
            "物理实验", "化学实验", "生物实验", "工程实验",
            "材料实验", "电子实验"
        ],
        "evaluation_dimensions": [
            {
                "key": "procedure",
                "name": "实验步骤",
                "name_en": "Procedure",
                "description": "实验步骤是否正确规范，操作是否标准"
            },
            {
                "key": "accuracy",
                "name": "数据准确性",
                "name_en": "Accuracy",
                "description": "实验数据是否准确可靠，记录是否完整"
            },
            {
                "key": "analysis",
                "name": "结果分析",
                "name_en": "Analysis",
                "description": "对实验结果的分析是否合理，结论是否正确"
            },
            {
                "key": "report",
                "name": "报告质量",
                "name_en": "Report",
                "description": "实验报告是否完整规范，图表是否清晰"
            }
        ]
    },
    
    # ===== 数学类课程 =====
    "mathematics": {
        "name": "数学推导类",
        "name_en": "Mathematics",
        "subjects": [
            "高等数学", "线性代数", "概率论", "离散数学",
            "数学分析", "抽象代数", "数理统计"
        ],
        "evaluation_dimensions": [
            {
                "key": "correctness",
                "name": "正确性",
                "name_en": "Correctness",
                "description": "推导过程和结果是否正确，计算是否准确"
            },
            {
                "key": "rigor",
                "name": "严谨性",
                "name_en": "Rigor",
                "description": "数学表述是否严谨规范，证明是否严密"
            },
            {
                "key": "completeness",
                "name": "完整性",
                "name_en": "Completeness",
                "description": "证明是否完整，步骤是否齐全，无跳跃"
            },
            {
                "key": "clarity",
                "name": "清晰度",
                "name_en": "Clarity",
                "description": "推导思路是否清晰易懂，表达是否简洁"
            }
        ]
    },
    
    # ===== 通用类型（兜底） =====
    "generic": {
        "name": "通用课程",
        "name_en": "Generic",
        "subjects": [],  # 匹配所有未指定的课程
        "evaluation_dimensions": [
            {
                "key": "content_quality",
                "name": "内容质量",
                "name_en": "Content Quality",
                "description": "作业内容的质量和完成度，是否符合要求"
            },
            {
                "key": "understanding",
                "name": "理解程度",
                "name_en": "Understanding",
                "description": "对知识点的理解和掌握程度"
            },
            {
                "key": "effort",
                "name": "努力程度",
                "name_en": "Effort",
                "description": "在作业中投入的精力和认真程度"
            },
            {
                "key": "presentation",
                "name": "呈现质量",
                "name_en": "Presentation",
                "description": "作业呈现的清晰度和规范性"
            }
        ]
    }
}


# 便捷访问函数
def get_course_types() -> List[str]:
    """获取所有课程类型"""
    return list(COURSE_TEMPLATES.keys())


def get_course_template(course_type: str) -> Dict[str, Any]:
    """获取课程模板"""
    return COURSE_TEMPLATES.get(course_type, COURSE_TEMPLATES["generic"])


def get_subjects_by_type(course_type: str) -> List[str]:
    """获取课程类型对应的科目列表"""
    template = get_course_template(course_type)
    return template.get("subjects", [])
