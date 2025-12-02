"""
心理学模型 - 实现学生的情绪、动机、社交关系和语言风格系统
让AI学生更像真人
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from enum import Enum
import random
import math
from datetime import datetime


# ============================================
# 1. 情绪与动机系统 (Emotion & Motivation System)
# ============================================

class MoodState(str, Enum):
    """情绪状态枚举"""
    EXCITED = "excited"        # 兴奋
    CONFIDENT = "confident"    # 自信
    NEUTRAL = "neutral"        # 平静
    ANXIOUS = "anxious"        # 焦虑
    FRUSTRATED = "frustrated"  # 挫败
    BORED = "bored"           # 无聊
    TIRED = "tired"           # 疲惫


class MotivationType(str, Enum):
    """动机类型"""
    INTRINSIC = "intrinsic"       # 内在动机（对知识的兴趣）
    EXTRINSIC = "extrinsic"       # 外在动机（为了分数）
    SOCIAL = "social"             # 社交动机（为了获得认可）
    AVOIDANCE = "avoidance"       # 回避动机（避免失败）


class EmotionState(BaseModel):
    """学生情绪状态模型"""
    
    # 核心情绪维度 (0-1)
    motivation: float = Field(default=0.7, ge=0.0, le=1.0, description="动机水平")
    confidence: float = Field(default=0.6, ge=0.0, le=1.0, description="自信心")
    frustration: float = Field(default=0.2, ge=0.0, le=1.0, description="挫败感")
    fatigue: float = Field(default=0.1, ge=0.0, le=1.0, description="疲劳度")
    interest: float = Field(default=0.6, ge=0.0, le=1.0, description="兴趣程度")
    
    # 当前主导情绪
    current_mood: MoodState = Field(default=MoodState.NEUTRAL)
    
    # 主要动机类型
    primary_motivation: MotivationType = Field(default=MotivationType.EXTRINSIC)
    
    # 情绪历史（用于检测趋势）
    mood_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def update_after_feedback(self, feedback_sentiment: float, score: float, expected_score: float):
        """
        收到反馈后更新情绪状态
        
        Args:
            feedback_sentiment: 反馈情感倾向 (-1到1, 负面到正面)
            score: 实际得分 (0-100)
            expected_score: 期望得分 (0-100)
        """
        score_gap = (score - expected_score) / 100.0
        
        # 更新自信心
        if score_gap > 0.1:  # 超出预期
            self.confidence = min(1.0, self.confidence + 0.1 + score_gap * 0.2)
            self.frustration = max(0.0, self.frustration - 0.15)
        elif score_gap < -0.1:  # 低于预期
            self.confidence = max(0.0, self.confidence - 0.1 + score_gap * 0.15)
            self.frustration = min(1.0, self.frustration + 0.1 - score_gap * 0.2)
        
        # 根据反馈情感更新动机
        if feedback_sentiment > 0.3:  # 正面反馈
            self.motivation = min(1.0, self.motivation + 0.1)
            self.interest = min(1.0, self.interest + 0.05)
        elif feedback_sentiment < -0.3:  # 负面反馈
            # 负面反馈的影响取决于学生的韧性
            resilience = self.confidence * 0.5 + (1 - self.frustration) * 0.5
            self.motivation = max(0.2, self.motivation - 0.1 * (1 - resilience))
        
        # 更新主导情绪
        self._update_current_mood()
        
        # 记录历史
        self.mood_history.append({
            "timestamp": datetime.now().isoformat(),
            "mood": self.current_mood.value,
            "motivation": self.motivation,
            "confidence": self.confidence,
            "trigger": "feedback"
        })
    
    def update_after_work_completion(self, effort_level: float, perceived_quality: float):
        """
        完成作业后更新情绪
        
        Args:
            effort_level: 投入程度 (0-1)
            perceived_quality: 自我感知的质量 (0-1)
        """
        # 高投入+高质量 -> 满足感
        if effort_level > 0.7 and perceived_quality > 0.7:
            self.confidence = min(1.0, self.confidence + 0.05)
            self.motivation = min(1.0, self.motivation + 0.03)
        
        # 疲劳累积
        self.fatigue = min(1.0, self.fatigue + effort_level * 0.15)
        
        self._update_current_mood()
    
    def apply_time_decay(self, days_passed: float = 1.0):
        """
        时间衰减效应
        
        Args:
            days_passed: 经过的天数
        """
        # 挫败感随时间减轻
        self.frustration = max(0.0, self.frustration - 0.05 * days_passed)
        
        # 疲劳恢复
        self.fatigue = max(0.0, self.fatigue - 0.1 * days_passed)
        
        # 动机缓慢恢复到基线
        baseline_motivation = 0.6
        if self.motivation < baseline_motivation:
            self.motivation = min(baseline_motivation, self.motivation + 0.03 * days_passed)
        
        self._update_current_mood()
    
    def _update_current_mood(self):
        """根据各维度更新主导情绪"""
        if self.fatigue > 0.7:
            self.current_mood = MoodState.TIRED
        elif self.frustration > 0.6:
            self.current_mood = MoodState.FRUSTRATED
        elif self.motivation < 0.3:
            self.current_mood = MoodState.BORED
        elif self.confidence > 0.8 and self.motivation > 0.7:
            self.current_mood = MoodState.EXCITED
        elif self.confidence > 0.6:
            self.current_mood = MoodState.CONFIDENT
        elif self.frustration > 0.4 or self.confidence < 0.4:
            self.current_mood = MoodState.ANXIOUS
        else:
            self.current_mood = MoodState.NEUTRAL
    
    def get_performance_modifier(self) -> float:
        """
        获取情绪对表现的影响系数
        
        Returns:
            float: 表现修正系数 (0.7 - 1.2)
        """
        # 基础修正
        modifier = 1.0
        
        # 动机影响
        modifier += (self.motivation - 0.5) * 0.2
        
        # 自信影响
        modifier += (self.confidence - 0.5) * 0.1
        
        # 负面因素
        modifier -= self.frustration * 0.15
        modifier -= self.fatigue * 0.1
        
        return max(0.7, min(1.2, modifier))
    
    def get_evaluation_style_modifier(self) -> Dict[str, float]:
        """
        获取情绪对评价风格的影响
        
        Returns:
            Dict: 评价风格修正参数
        """
        return {
            "score_bias": (self.motivation - 0.5) * 0.1,  # 动机高时给分稍高
            "detail_level": self.motivation * 0.5 + (1 - self.fatigue) * 0.5,  # 详细程度
            "positivity": self.confidence * 0.3 + (1 - self.frustration) * 0.3,  # 正面程度
            "patience": (1 - self.fatigue) * (1 - self.frustration)  # 耐心程度
        }


# ============================================
# 2. 社交关系系统 (Social Relationship System)
# ============================================

class RelationshipType(str, Enum):
    """关系类型"""
    STRANGER = "stranger"      # 陌生人
    ACQUAINTANCE = "acquaintance"  # 认识
    CLASSMATE = "classmate"    # 普通同学
    FRIEND = "friend"          # 朋友
    CLOSE_FRIEND = "close_friend"  # 好朋友
    RIVAL = "rival"            # 竞争对手


class SocialRelationship(BaseModel):
    """学生社交关系模型"""
    
    # 与其他学生的关系亲密度 {student_id: 亲密度(-1到1)}
    relationships: Dict[str, float] = Field(default_factory=dict)
    
    # 互惠记忆 {student_id: 上次给我的评分偏差}
    reciprocity_memory: Dict[str, float] = Field(default_factory=dict)
    
    # 在班级中的声誉 (0-1)
    reputation: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # 社交倾向
    sociability: float = Field(default=0.5, ge=0.0, le=1.0, description="社交性")
    conformity: float = Field(default=0.5, ge=0.0, le=1.0, description="从众性")
    reciprocity_tendency: float = Field(default=0.5, ge=0.0, le=1.0, description="互惠倾向")
    
    # 关系类型缓存
    relationship_types: Dict[str, RelationshipType] = Field(default_factory=dict)
    
    def get_relationship_with(self, other_student_id: str) -> float:
        """获取与某学生的关系亲密度"""
        return self.relationships.get(other_student_id, 0.0)
    
    def update_relationship(self, other_student_id: str, interaction_quality: float):
        """
        根据交互更新关系
        
        Args:
            other_student_id: 对方学生ID
            interaction_quality: 交互质量 (-1到1)
        """
        current = self.relationships.get(other_student_id, 0.0)
        # 关系变化有惯性，不会突变
        change = interaction_quality * 0.2
        new_value = max(-1.0, min(1.0, current + change))
        self.relationships[other_student_id] = new_value
        
        # 更新关系类型
        self._update_relationship_type(other_student_id, new_value)
    
    def record_evaluation_received(self, evaluator_id: str, score: float, expected_score: float):
        """
        记录收到的评价（用于互惠效应）
        
        Args:
            evaluator_id: 评价者ID
            score: 收到的分数
            expected_score: 期望分数
        """
        score_deviation = (score - expected_score) / 100.0
        self.reciprocity_memory[evaluator_id] = score_deviation
        
        # 根据评价好坏更新关系
        if score_deviation > 0.1:  # 给了好评
            self.update_relationship(evaluator_id, 0.3)
        elif score_deviation < -0.1:  # 给了差评
            self.update_relationship(evaluator_id, -0.2)
    
    def get_evaluation_bias(self, target_student_id: str) -> float:
        """
        获取对某学生评价时的偏差
        
        Args:
            target_student_id: 被评价学生ID
            
        Returns:
            float: 分数偏差 (-15 到 +15)
        """
        bias = 0.0
        
        # 1. 关系影响
        relationship = self.get_relationship_with(target_student_id)
        bias += relationship * 8  # 好朋友可能+8分，仇人可能-8分
        
        # 2. 互惠效应
        if target_student_id in self.reciprocity_memory:
            reciprocity = self.reciprocity_memory[target_student_id]
            bias += reciprocity * 100 * 0.5  # 对方给我高分，我倾向于给对方高分
        
        # 3. 声誉影响（名声好的学生可能得到更宽松的评价）
        # 这里假设target的声誉我们不知道，所以只用自己的从众性
        
        # 限制偏差范围
        return max(-15, min(15, bias))
    
    def _update_relationship_type(self, other_id: str, intimacy: float):
        """根据亲密度更新关系类型"""
        if intimacy >= 0.7:
            self.relationship_types[other_id] = RelationshipType.CLOSE_FRIEND
        elif intimacy >= 0.4:
            self.relationship_types[other_id] = RelationshipType.FRIEND
        elif intimacy >= 0.1:
            self.relationship_types[other_id] = RelationshipType.CLASSMATE
        elif intimacy >= -0.3:
            self.relationship_types[other_id] = RelationshipType.ACQUAINTANCE
        elif intimacy >= -0.6:
            self.relationship_types[other_id] = RelationshipType.STRANGER
        else:
            self.relationship_types[other_id] = RelationshipType.RIVAL
    
    def update_reputation(self, evaluation_quality: float, peer_recognition: float):
        """
        更新声誉
        
        Args:
            evaluation_quality: 评价质量 (0-1)
            peer_recognition: 同伴认可度 (0-1)
        """
        # 声誉缓慢变化
        change = (evaluation_quality * 0.3 + peer_recognition * 0.3 - 0.3) * 0.1
        self.reputation = max(0.0, min(1.0, self.reputation + change))


# ============================================
# 3. 语言风格系统 (Language Style System)
# ============================================

class LanguageStyle(BaseModel):
    """学生语言风格模型"""
    
    # 基础风格参数 (0-1)
    formality: float = Field(default=0.5, ge=0.0, le=1.0, description="正式程度")
    verbosity: float = Field(default=0.5, ge=0.0, le=1.0, description="详细程度")
    emoji_tendency: float = Field(default=0.3, ge=0.0, le=1.0, description="表情使用倾向")
    typo_rate: float = Field(default=0.05, ge=0.0, le=0.3, description="错别字率")
    
    # 句式偏好
    preferred_patterns: List[str] = Field(default_factory=list)
    
    # 常用开场白
    opening_phrases: List[str] = Field(default_factory=list)
    
    # 常用结束语
    closing_phrases: List[str] = Field(default_factory=list)
    
    # 口头禅/习惯用语
    catchphrases: List[str] = Field(default_factory=list)
    
    # 语气词使用
    filler_words: List[str] = Field(default_factory=list)
    
    @classmethod
    def create_for_student_type(cls, student_type: str, personality_traits: Dict[str, float]) -> "LanguageStyle":
        """
        根据学生类型创建语言风格
        
        Args:
            student_type: 学生类型
            personality_traits: 性格特征
        """
        style = cls()
        
        if student_type == "excellent":
            style.formality = random.uniform(0.6, 0.8)
            style.verbosity = random.uniform(0.6, 0.8)
            style.emoji_tendency = random.uniform(0.1, 0.3)
            style.typo_rate = random.uniform(0.0, 0.02)
            style.opening_phrases = [
                "整体来看，", "从专业角度分析，", "认真审阅后，",
                "综合考虑各方面，", "仔细阅读后，"
            ]
            style.closing_phrases = [
                "总的来说，作业完成度不错。", "期待看到进一步的改进。",
                "建议继续保持这种学习态度。", "希望这些建议对你有帮助。"
            ]
            style.catchphrases = ["值得肯定的是", "需要注意的是", "建议", "可以考虑"]
            style.filler_words = []
            
        elif student_type == "good":
            style.formality = random.uniform(0.5, 0.7)
            style.verbosity = random.uniform(0.5, 0.7)
            style.emoji_tendency = random.uniform(0.2, 0.4)
            style.typo_rate = random.uniform(0.01, 0.05)
            style.opening_phrases = [
                "看了你的作业，", "总体感觉", "我觉得",
                "认真看完后，", "我的看法是"
            ]
            style.closing_phrases = [
                "加油！", "继续努力~", "整体不错的！",
                "期待你的进步！", "希望有帮助"
            ]
            style.catchphrases = ["挺好的", "不错", "可以改进一下", "我觉得"]
            style.filler_words = ["嗯", "然后"]
            
        elif student_type == "average":
            style.formality = random.uniform(0.3, 0.5)
            style.verbosity = random.uniform(0.4, 0.6)
            style.emoji_tendency = random.uniform(0.3, 0.5)
            style.typo_rate = random.uniform(0.03, 0.08)
            style.opening_phrases = [
                "看了一下，", "emmm", "怎么说呢",
                "大概看了下，", "感觉"
            ]
            style.closing_phrases = [
                "大概就这些吧", "就这样~", "加油",
                "差不多就这样", "希望有用"
            ]
            style.catchphrases = ["感觉", "好像", "可能", "大概"]
            style.filler_words = ["emmm", "额", "那个"]
            
        elif student_type == "below_average":
            style.formality = random.uniform(0.2, 0.4)
            style.verbosity = random.uniform(0.3, 0.5)
            style.emoji_tendency = random.uniform(0.4, 0.6)
            style.typo_rate = random.uniform(0.05, 0.15)
            style.opening_phrases = [
                "我看了下", "额...", "嗯...",
                "大概看了一下", "我感觉"
            ]
            style.closing_phrases = [
                "就这样吧", "不知道对不对", "我也不太懂",
                "差不多吧", "emmm就这些"
            ]
            style.catchphrases = ["可能", "好像", "不太懂", "感觉"]
            style.filler_words = ["额", "嗯", "那个", "就是"]
            
        elif student_type == "strict":
            style.formality = random.uniform(0.7, 0.9)
            style.verbosity = random.uniform(0.7, 0.9)
            style.emoji_tendency = random.uniform(0.0, 0.1)
            style.typo_rate = random.uniform(0.0, 0.02)
            style.opening_phrases = [
                "经过仔细审阅，", "必须指出的是，", "客观来说，",
                "从严格标准来看，", "直言不讳地说，"
            ]
            style.closing_phrases = [
                "以上问题需要认真对待。", "希望能够正视这些不足。",
                "标准就是标准，不能降低要求。", "请认真修改。"
            ]
            style.catchphrases = ["问题在于", "明显的不足", "需要改进", "不够"]
            style.filler_words = []
            
        elif student_type == "lenient":
            style.formality = random.uniform(0.3, 0.5)
            style.verbosity = random.uniform(0.4, 0.6)
            style.emoji_tendency = random.uniform(0.5, 0.8)
            style.typo_rate = random.uniform(0.02, 0.06)
            style.opening_phrases = [
                "哇，做得不错！", "整体很棒！", "看得出来很用心~",
                "首先要说，做得挺好的！", "辛苦啦！"
            ]
            style.closing_phrases = [
                "加油加油！💪", "继续保持！", "很棒了！",
                "相信你会越来越好的~", "期待你的进步！✨"
            ]
            style.catchphrases = ["很棒", "不错", "挺好", "继续加油"]
            style.filler_words = ["哈哈", "~", "！"]
            
        elif student_type == "perfunctory":
            style.formality = random.uniform(0.1, 0.3)
            style.verbosity = random.uniform(0.1, 0.3)
            style.emoji_tendency = random.uniform(0.3, 0.7)
            style.typo_rate = random.uniform(0.08, 0.2)
            style.opening_phrases = [
                "还行", "可以", "嗯",
                "看了", "行吧"
            ]
            style.closing_phrases = [
                "就这样", "差不多", "可以了",
                "行", "没啥问题"
            ]
            style.catchphrases = ["还行", "可以", "行", "嗯"]
            style.filler_words = ["嗯", "哦", "额"]
        
        else:
            # 默认风格
            style.opening_phrases = ["看了你的作业，", "总体来说，"]
            style.closing_phrases = ["继续加油！", "希望有帮助。"]
        
        return style
    
    def apply_style_to_comment(self, comment: str, mood: MoodState = MoodState.NEUTRAL) -> str:
        """
        将语言风格应用到评语
        
        Args:
            comment: 原始评语
            mood: 当前情绪状态
            
        Returns:
            str: 风格化后的评语
        """
        styled_comment = comment
        
        # 1. 添加开场白（根据详细程度和正式程度）
        if self.verbosity > 0.5 and random.random() < 0.7:
            opening = random.choice(self.opening_phrases) if self.opening_phrases else ""
            if opening and not styled_comment.startswith(opening):
                styled_comment = opening + styled_comment
        
        # 2. 添加语气词（非正式场合）
        if self.formality < 0.5 and self.filler_words and random.random() < 0.4:
            # 在句子中间插入语气词
            sentences = styled_comment.split('。')
            if len(sentences) > 2:
                insert_pos = random.randint(1, len(sentences) - 2)
                filler = random.choice(self.filler_words)
                sentences[insert_pos] = filler + "，" + sentences[insert_pos].lstrip()
                styled_comment = '。'.join(sentences)
        
        # 3. 添加表情（根据emoji倾向和情绪）
        if self.emoji_tendency > 0.3 and random.random() < self.emoji_tendency:
            emojis_by_mood = {
                MoodState.EXCITED: ["✨", "🎉", "💪", "👍"],
                MoodState.CONFIDENT: ["👍", "✅", "💯"],
                MoodState.NEUTRAL: ["~", "。", ""],
                MoodState.ANXIOUS: ["😅", "🤔", ""],
                MoodState.FRUSTRATED: ["😤", "💢", ""],
                MoodState.BORED: ["😐", "🙃", ""],
                MoodState.TIRED: ["😴", "🥱", ""]
            }
            emoji_list = emojis_by_mood.get(mood, [""])
            emoji = random.choice(emoji_list)
            if emoji:
                styled_comment = styled_comment.rstrip('。！') + emoji
        
        # 4. 添加结束语
        if self.verbosity > 0.4 and random.random() < 0.5:
            closing = random.choice(self.closing_phrases) if self.closing_phrases else ""
            if closing and not styled_comment.endswith(closing):
                styled_comment = styled_comment.rstrip('。！~') + ' ' + closing
        
        # 5. 模拟错别字（只在非正式且有错别字倾向时）
        if self.typo_rate > 0.05 and self.formality < 0.5:
            styled_comment = self._introduce_typos(styled_comment)
        
        # 6. 调整标点符号风格
        if self.formality < 0.4:
            # 非正式：使用更多感叹号和波浪号
            styled_comment = styled_comment.replace('。', random.choice(['！', '~', '。']))
        
        return styled_comment
    
    def _introduce_typos(self, text: str) -> str:
        """模拟错别字（轻微）"""
        # 常见的同音字替换
        typo_map = {
            "的": ["得", "地"],
            "得": ["的", "地"],
            "在": ["再"],
            "再": ["在"],
            "做": ["作"],
            "作": ["做"],
        }
        
        result = list(text)
        for i, char in enumerate(result):
            if char in typo_map and random.random() < self.typo_rate:
                result[i] = random.choice(typo_map[char])
        
        return ''.join(result)
    
    def get_comment_length_modifier(self) -> float:
        """获取评语长度修正系数"""
        # verbosity 0.0 -> 0.5倍长度
        # verbosity 1.0 -> 1.5倍长度
        return 0.5 + self.verbosity


# ============================================
# 4. 综合心理模型 (Integrated Psychology Model)
# ============================================

class StudentPsychology(BaseModel):
    """学生综合心理模型 - 整合情绪、社交和语言风格"""
    
    emotion: EmotionState = Field(default_factory=EmotionState)
    social: SocialRelationship = Field(default_factory=SocialRelationship)
    language: LanguageStyle = Field(default_factory=LanguageStyle)
    
    # 学生基本信息引用
    student_id: str = ""
    student_type: str = "average"
    
    @classmethod
    def create_for_student(cls, student_id: str, student_type: str, 
                          personality_traits: Dict[str, float]) -> "StudentPsychology":
        """
        为学生创建心理模型
        
        Args:
            student_id: 学生ID
            student_type: 学生类型
            personality_traits: 性格特征
        """
        psychology = cls()
        psychology.student_id = student_id
        psychology.student_type = student_type
        
        # 初始化情绪状态（根据学生类型）
        if student_type == "excellent":
            psychology.emotion.motivation = random.uniform(0.7, 0.9)
            psychology.emotion.confidence = random.uniform(0.7, 0.9)
            psychology.emotion.primary_motivation = MotivationType.INTRINSIC
        elif student_type == "good":
            psychology.emotion.motivation = random.uniform(0.6, 0.8)
            psychology.emotion.confidence = random.uniform(0.6, 0.8)
        elif student_type == "average":
            psychology.emotion.motivation = random.uniform(0.4, 0.6)
            psychology.emotion.confidence = random.uniform(0.4, 0.6)
        elif student_type == "below_average":
            psychology.emotion.motivation = random.uniform(0.3, 0.5)
            psychology.emotion.confidence = random.uniform(0.3, 0.5)
            psychology.emotion.frustration = random.uniform(0.2, 0.4)
        elif student_type == "perfunctory":
            psychology.emotion.motivation = random.uniform(0.2, 0.4)
            psychology.emotion.interest = random.uniform(0.2, 0.4)
            psychology.emotion.primary_motivation = MotivationType.AVOIDANCE
        
        # 初始化社交属性
        psychology.social.sociability = personality_traits.get("外向", 0.5)
        psychology.social.conformity = personality_traits.get("随和", 0.5)
        
        # 初始化语言风格
        psychology.language = LanguageStyle.create_for_student_type(student_type, personality_traits)
        
        return psychology
    
    def get_total_evaluation_bias(self, target_student_id: str) -> float:
        """
        获取对某学生评价的总偏差
        
        Args:
            target_student_id: 被评价学生ID
            
        Returns:
            float: 总分数偏差
        """
        bias = 0.0
        
        # 1. 社交关系偏差
        social_bias = self.social.get_evaluation_bias(target_student_id)
        bias += social_bias
        
        # 2. 情绪影响
        emotion_modifier = self.emotion.get_evaluation_style_modifier()
        bias += emotion_modifier["score_bias"] * 10  # 转换为分数
        
        return bias
    
    def process_feedback_event(self, evaluator_id: str, score: float, 
                              expected_score: float, feedback_text: str):
        """
        处理收到反馈的事件
        
        Args:
            evaluator_id: 评价者ID
            score: 收到的分数
            expected_score: 期望分数
            feedback_text: 反馈文本
        """
        # 简单的情感分析（可以后续改用LLM）
        positive_words = ["好", "棒", "优秀", "不错", "赞", "很好", "excellent", "good"]
        negative_words = ["差", "问题", "不足", "错误", "改进", "缺少", "需要"]
        
        positive_count = sum(1 for word in positive_words if word in feedback_text)
        negative_count = sum(1 for word in negative_words if word in feedback_text)
        
        sentiment = (positive_count - negative_count) / max(1, positive_count + negative_count)
        
        # 更新情绪
        self.emotion.update_after_feedback(sentiment, score, expected_score)
        
        # 更新社交关系
        self.social.record_evaluation_received(evaluator_id, score, expected_score)
    
    def to_prompt_context(self) -> str:
        """
        生成用于提示词的心理状态描述
        
        Returns:
            str: 心理状态描述文本
        """
        mood_descriptions = {
            MoodState.EXCITED: "你现在心情很好，对学习充满热情",
            MoodState.CONFIDENT: "你对自己很有信心",
            MoodState.NEUTRAL: "你现在心态比较平和",
            MoodState.ANXIOUS: "你有些焦虑和不安",
            MoodState.FRUSTRATED: "你最近有些挫败感",
            MoodState.BORED: "你对这门课有点提不起兴趣",
            MoodState.TIRED: "你最近有点疲惫"
        }
        
        context = f"""
当前心理状态：
- {mood_descriptions.get(self.emotion.current_mood, "状态正常")}
- 学习动机：{'较高' if self.emotion.motivation > 0.6 else '一般' if self.emotion.motivation > 0.4 else '较低'}
- 自信程度：{'很有信心' if self.emotion.confidence > 0.7 else '比较自信' if self.emotion.confidence > 0.5 else '有些不自信'}
"""
        return context.strip()
    
    @classmethod
    def create_default(cls, student_type: str = "average") -> "StudentPsychology":
        """
        创建默认心理状态（简化版）
        
        Args:
            student_type: 学生类型
            
        Returns:
            StudentPsychology: 默认心理状态
        """
        return cls.create_for_student(
            student_id="",
            student_type=student_type,
            personality_traits={}
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        序列化为字典
        
        Returns:
            Dict: 心理状态字典
        """
        return {
            "student_id": self.student_id,
            "student_type": self.student_type,
            "emotion": {
                "motivation": self.emotion.motivation,
                "confidence": self.emotion.confidence,
                "frustration": self.emotion.frustration,
                "fatigue": self.emotion.fatigue,
                "interest": self.emotion.interest,
                "current_mood": self.emotion.current_mood.value,
                "primary_motivation": self.emotion.primary_motivation.value,
                "mood_history": self.emotion.mood_history
            },
            "social": {
                "relationships": self.social.relationships,
                "reciprocity_memory": self.social.reciprocity_memory,
                "sociability": self.social.sociability,
                "conformity": self.social.conformity,
                "reciprocity_tendency": self.social.reciprocity_tendency,
                "reputation": self.social.reputation
            },
            "language": {
                "formality": self.language.formality,
                "verbosity": self.language.verbosity,
                "emoji_tendency": self.language.emoji_tendency,
                "typo_rate": self.language.typo_rate,
                "opening_phrases": self.language.opening_phrases,
                "closing_phrases": self.language.closing_phrases,
                "catchphrases": self.language.catchphrases
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StudentPsychology":
        """
        从字典反序列化
        
        Args:
            data: 心理状态字典
            
        Returns:
            StudentPsychology: 心理状态对象
        """
        psychology = cls()
        
        psychology.student_id = data.get("student_id", "")
        psychology.student_type = data.get("student_type", "average")
        
        # 恢复情绪状态
        emotion_data = data.get("emotion", {})
        psychology.emotion.motivation = emotion_data.get("motivation", 0.5)
        psychology.emotion.confidence = emotion_data.get("confidence", 0.5)
        psychology.emotion.frustration = emotion_data.get("frustration", 0.2)
        psychology.emotion.fatigue = emotion_data.get("fatigue", 0.1)
        psychology.emotion.interest = emotion_data.get("interest", 0.6)
        
        if "current_mood" in emotion_data:
            psychology.emotion.current_mood = MoodState(emotion_data["current_mood"])
        if "primary_motivation" in emotion_data:
            psychology.emotion.primary_motivation = MotivationType(emotion_data["primary_motivation"])
        
        psychology.emotion.mood_history = emotion_data.get("mood_history", [])
        
        # 恢复社交关系
        social_data = data.get("social", {})
        psychology.social.relationships = social_data.get("relationships", {})
        psychology.social.reciprocity_memory = social_data.get("reciprocity_memory", {})
        psychology.social.sociability = social_data.get("sociability", 0.5)
        psychology.social.conformity = social_data.get("conformity", 0.5)
        psychology.social.reciprocity_tendency = social_data.get("reciprocity_tendency", 0.5)
        psychology.social.reputation = social_data.get("reputation", 0.5)
        
        # 恢复语言风格
        language_data = data.get("language", {})
        psychology.language.formality = language_data.get("formality", 0.5)
        psychology.language.verbosity = language_data.get("verbosity", 0.5)
        psychology.language.emoji_tendency = language_data.get("emoji_tendency", 0.3)
        psychology.language.typo_rate = language_data.get("typo_rate", 0.05)
        psychology.language.opening_phrases = language_data.get("opening_phrases", [])
        psychology.language.closing_phrases = language_data.get("closing_phrases", [])
        psychology.language.catchphrases = language_data.get("catchphrases", [])
        
        return psychology
        
        return psychology
    
    def update_mood_after_feedback(self, feedback_score: float, is_positive: bool):
        """
        收到反馈后更新情绪（简化版）
        
        Args:
            feedback_score: 反馈分数 (0-1)
            is_positive: 是否正面反馈
        """
        if is_positive:
            self.emotion.motivation = min(1.0, self.emotion.motivation + 0.05)
            self.emotion.confidence = min(1.0, self.emotion.confidence + 0.03)
            self.emotion.frustration = max(0.0, self.emotion.frustration - 0.05)
        else:
            self.emotion.frustration = min(1.0, self.emotion.frustration + 0.1)
            self.emotion.motivation = max(0.2, self.emotion.motivation - 0.05)
            self.emotion.confidence = max(0.1, self.emotion.confidence - 0.05)

