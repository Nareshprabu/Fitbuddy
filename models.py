from typing import List, Optional, Dict, Any
try:
    from pydantic import BaseModel, Field
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def dict(self):
            return self.__dict__
    def Field(default=None, **kwargs):
        return default

class Exercise(BaseModel):
    name: str = Field(..., description="Name of the exercise")
    muscle_group: str = Field(..., description="Target muscle group")
    sets: str = Field(..., description="Target sets (e.g. '3-4')")
    reps: str = Field(..., description="Target repetitions (e.g. '8-10')")
    rest: str = Field(..., description="Rest interval between sets (e.g. '60s')")
    coaching_tip: Optional[str] = Field(default=None, description="Form cue or coaching tip")

class DaySchedule(BaseModel):
    day_number: int = Field(..., ge=1, le=7)
    day_name: str = Field(..., example="Day 1 - Monday")
    focus: str = Field(..., example="Upper Body Hypertrophy")
    warm_up: str = Field(..., description="Dynamic warm-up protocol")
    exercises: List[Exercise]
    cool_down: str = Field(..., description="Cool-down and static stretching")
    duration_minutes: int = Field(default=45, example=50)
    intensity_level: str = Field(default="medium", example="medium")

class PlanData(BaseModel):
    title: str
    summary: str
    overview: Optional[str] = None
    weekly_goal_focus: Optional[str] = None
    general_recovery_tip: Optional[str] = None
    days: List[DaySchedule]

class UserCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, example="Alex Morgan")
    age: int = Field(..., ge=14, le=100, example=28)
    weight: float = Field(..., gt=20, le=300, example=72.5)
    weight_unit: str = Field(default="kg", example="kg")
    goal: str = Field(..., example="muscle gain")
    intensity: str = Field(..., example="medium")
    equipment: Optional[str] = Field(default="full gym", example="full gym")
    notes: Optional[str] = Field(default="", example="No spinal injuries")

class GeneratePlanRequest(UserCreate):
    pass

class RegeneratePlanRequest(BaseModel):
    plan_id: int = Field(..., example=1, description="ID of the plan to update")
    feedback_text: str = Field(..., min_length=3, example="more focus on cardio and include more rest days")

class NutritionTipRequest(BaseModel):
    goal: str = Field(..., example="muscle gain")
    category: Optional[str] = Field(default="nutrition", example="nutrition")
    user_id: Optional[int] = Field(default=None, example=1)

class NutritionTipResponse(BaseModel):
    id: Optional[int] = None
    goal: str
    category: str
    tip_title: str
    tip_content: str
    action_step: Optional[str] = None
    model_used: Optional[str] = None
    generated_by: Optional[str] = None
    created_at: Optional[str] = None

class WorkoutPlanSummary(BaseModel):
    id: int
    user_id: int
    version: int
    title: str
    summary: Optional[str]
    goal: str
    intensity: str
    model_used: Optional[str]
    is_active: bool
    created_at: str

class MealPlanRequest(BaseModel):
    goal: str = Field(..., example="weight loss")
    diet_preference: Optional[str] = Field(default="omnivore", example="vegetarian")
    calories_target: Optional[int] = Field(default=2000, example=2000)
    language: Optional[str] = Field(default="en", example="en")
    user_id: Optional[int] = Field(default=None, example=1)

class CoachQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, example="What should I eat within 30 minutes after my workout?")
    context: Optional[str] = Field(default="", example="Goal: muscle gain, age: 28")
    language: Optional[str] = Field(default="en", example="en")

class ProgressLogCreate(BaseModel):
    user_id: int = Field(..., example=1)
    log_date: str = Field(..., example="2026-10-03")
    weight: float = Field(..., gt=20, le=300, example=72.0)
    workouts_completed: Optional[int] = Field(default=1, example=1)
    calories_burned: Optional[int] = Field(default=450, example=450)
    steps: Optional[int] = Field(default=8500, example=8500)
    avg_heart_rate: Optional[int] = Field(default=138, example=138)
    notes: Optional[str] = Field(default="", example="Felt energized, great squat session")

