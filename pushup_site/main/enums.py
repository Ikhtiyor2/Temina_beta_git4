# main/enums.py
from enum import Enum

class ExerciseType(Enum):
    PUSHUPS = "pushups"
    SQUATS = "squats" 
    CRUNCHES = "crunches"
    PULLUPS = "pullups"
    COMBO = "combo"
    TIMED_SET = "timed_set"

class FeedbackType(Enum):
    CORRECT = "correct"
    WARNING = "warning" 
    ERROR = "error"

class WorkoutStage(Enum):
    UP = "up"
    DOWN = "down"
    READY = "ready"
    WAITING = "waiting"