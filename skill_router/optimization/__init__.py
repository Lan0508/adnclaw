"""Optimization modules: eval, diagnose, suggest, tune, golden."""

from skill_router.optimization.eval import run_eval, format_report, save_report, EvalReport, EvalResult
from skill_router.optimization.diagnose import run_diagnose, format_diagnoses, Diagnosis
from skill_router.optimization.suggest import generate_suggestions, format_suggestions, save_suggestions
from skill_router.optimization.tune import find_optimal_threshold, format_tune_result
from skill_router.optimization.golden import load_golden, add_golden, validate_new_case