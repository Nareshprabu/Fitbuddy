import os
import json
import re
import requests
from typing import Dict, Any, Optional

# ==============================================================================
# AI MODEL CONFIGURATION
# Gemini 1.5 Pro: Deep reasoning & multi-turn refinement for structured 7-day workouts
# Gemini Flash: Ultra-fast low-latency generation for concise nutrition & recovery guidance
# ==============================================================================
MODEL_WORKOUT_GEN = os.environ.get("GEMINI_WORKOUT_MODEL", "gemini-1.5-pro")
MODEL_NUTRITION_GEN = os.environ.get("GEMINI_NUTRITION_MODEL", "gemini-1.5-flash")

# Check if official google.generativeai SDK is available
try:
    import google.generativeai as genai
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

def get_api_key(explicit_key: Optional[str] = None) -> Optional[str]:
    """Retrieves API key from explicit parameter, or environment variables."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or None

def call_gemini(model_name: str, prompt: str, system_instruction: Optional[str] = None, api_key: Optional[str] = None) -> Optional[str]:
    """
    Calls Google Gemini using the official SDK if present, or direct REST API via requests.
    """
    key = get_api_key(api_key)
    if not key:
        return None

    # Method 1: Using google-generativeai SDK if installed
    if HAS_GENAI_SDK:
        try:
            genai.configure(api_key=key)
            generation_config = {
                "temperature": 0.3 if "pro" in model_name else 0.5,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 4096,
            }
            model = genai.GenerativeModel(
                model_name=model_name,
                generation_config=generation_config,
                system_instruction=system_instruction
            )
            response = model.generate_content(prompt)
            if response and response.text:
                return response.text
        except Exception as e:
            print(f"GenAI SDK call failed ({e}); attempting direct REST fallback...")

    # Method 2: Direct REST API via requests (zero SDK dependency)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload: Dict[str, Any] = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.3 if "pro" in model_name else 0.5,
            "maxOutputTokens": 4000
        }
    }

    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=30)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "")
        else:
            print(f"Gemini REST API status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"Gemini REST API call error: {e}")

    return None

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Safely extracts and parses JSON payload from AI model response."""
    if not text:
        return None
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None

# ==============================================================================
# SCENARIO 1: Personalized 7-Day Workout Plan Generator (Gemini 1.5 Pro)
# ==============================================================================

def generate_workout_plan(name: str, age: int, weight: float, weight_unit: str, goal: str, intensity: str, equipment: str = "full gym", notes: str = "", api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Scenario 1:
    Engineered with Gemini 1.5 Pro to formulate safe, progressive, highly personalized
    7-day fitness schedules matching user demographics, target goals, and available equipment.
    """
    system_instruction = (
        "You are FitBuddy Master Personal Trainer & Sports Conditioning Specialist powered by Gemini 1.5 Pro. "
        "Formulate a scientifically calibrated, safe, highly engaging 7-day fitness routine. "
        "Output ONLY a valid JSON object matching the requested schema with no commentary outside JSON."
    )

    prompt = f"""
Client Profile:
- Client Name: {name}
- Age: {age} years
- Body Weight: {weight} {weight_unit}
- Primary Fitness Objective: {goal} (e.g. weight loss, muscle gain, general wellness, endurance, power)
- Preferred Workout Intensity: {intensity} (low, medium, high)
- Equipment Access: {equipment}
- Physical Considerations / Past Injuries: {notes if notes else 'None reported'}

Instructions:
1. Construct a comprehensive, day-by-day 7-day schedule (Day 1 through Day 7).
2. Balance progressive overload with necessary recovery / active mobility days.
3. Every single workout day must contain:
   - day_number (1 to 7)
   - day_name (e.g. "Day 1 - Monday")
   - focus (e.g. "Upper Body Hypertrophy & Chest/Back Focus")
   - warm_up (dynamic stretching & pulse-raiser, 5-8 mins)
   - duration_minutes (e.g. 45-60 mins based on intensity)
   - intensity_level ({intensity})
   - exercises list: array of exercise objects, each with:
       * name (e.g. "Barbell Bench Press")
       * muscle_group (e.g. "Pectoralis Major & Anterior Deltoids")
       * sets (e.g. "4")
       * reps (e.g. "8-10")
       * rest (e.g. "90s")
       * coaching_tip (concise form cue)
   - cool_down (static stretches & respiratory reset, 5 mins)

Return strictly this JSON schema:
{{
  "title": "Inspiring, descriptive title for the 7-day program",
  "summary": "2-3 sentence overview explaining why this routine fits {name}'s {goal} goal",
  "overview": "Detailed biomechanical methodology",
  "weekly_goal_focus": "Key milestone metric for the week",
  "general_recovery_tip": "High-yield recovery or nutrition recommendation",
  "days": [
     {{
       "day_number": 1,
       "day_name": "Day 1 - Monday",
       "focus": "...",
       "warm_up": "...",
       "duration_minutes": 50,
       "intensity_level": "{intensity}",
       "exercises": [
          {{
            "name": "...",
            "muscle_group": "...",
            "sets": "...",
            "reps": "...",
            "rest": "...",
            "coaching_tip": "..."
          }}
       ],
       "cool_down": "..."
     }}
  ]
}}
"""

    raw_text = call_gemini(MODEL_WORKOUT_GEN, prompt, system_instruction, api_key=api_key)
    parsed = extract_json_from_text(raw_text) if raw_text else None

    if parsed and "days" in parsed and len(parsed["days"]) >= 5:
        parsed["generated_by"] = f"Google {MODEL_WORKOUT_GEN}"
        parsed["model_used"] = MODEL_WORKOUT_GEN
        return parsed

    # Local Intelligent Fallback Engine
    fallback = _generate_smart_plan_fallback(name, age, weight, weight_unit, goal, intensity, equipment, notes)
    fallback["model_used"] = f"{MODEL_WORKOUT_GEN} (Simulated Engine)"
    return fallback

# ==============================================================================
# SCENARIO 2: Feedback-Based Workout Plan Updater (Gemini 1.5 Pro)
# ==============================================================================

def regenerate_workout_plan_with_feedback(current_plan: Dict[str, Any], feedback_text: str, user_info: Dict[str, Any], api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Scenario 2:
    Leverages Gemini 1.5 Pro's strong context window and reasoning capabilities to analyze
    the user's existing routine and dynamically adapt it based on user feedback.
    """
    system_instruction = (
        "You are FitBuddy AI Plan Refinement Specialist powered by Gemini 1.5 Pro. "
        "Iteratively refine an existing 7-day workout plan based on client feedback. "
        "Preserve core progression while modifying exercise selection, volume, rest days, or pacing to satisfy feedback. "
        "Output ONLY a valid JSON object matching the requested schema."
    )

    prompt = f"""
Client Overview:
- Name: {user_info.get('name', 'Client')}
- Age: {user_info.get('age', 28)}
- Weight: {user_info.get('weight', 70)} {user_info.get('weight_unit', 'kg')}
- Target Goal: {user_info.get('goal', 'wellness')}
- Current Intensity: {user_info.get('intensity', 'medium')}

Existing Plan Title: {current_plan.get('title', '7-Day Plan')}
Existing Plan Summary: {current_plan.get('summary', '')}

USER FEEDBACK REQUEST:
"{feedback_text}"

Task:
Regenerate and update the 7-day workout plan strictly addressing the feedback above (e.g. adding cardio intervals, substituting painful exercises, adding rest days, or altering session length).
Return valid JSON strictly matching:
{{
  "title": "Refined Plan Title highlighting updates",
  "summary": "Clear explanation of how user feedback '{feedback_text}' was incorporated",
  "overview": "Updated overview",
  "weekly_goal_focus": "Updated weekly target",
  "general_recovery_tip": "Updated recovery advice",
  "days": [
     {{
       "day_number": 1,
       "day_name": "Day 1 - Monday",
       "focus": "...",
       "warm_up": "...",
       "duration_minutes": 45,
       "intensity_level": "{user_info.get('intensity', 'medium')}",
       "exercises": [
          {{
            "name": "...",
            "muscle_group": "...",
            "sets": "...",
            "reps": "...",
            "rest": "...",
            "coaching_tip": "..."
          }}
       ],
       "cool_down": "..."
     }}
  ]
}}
Ensure all 7 days are provided.
"""

    raw_text = call_gemini(MODEL_WORKOUT_GEN, prompt, system_instruction, api_key=api_key)
    parsed = extract_json_from_text(raw_text) if raw_text else None

    if parsed and "days" in parsed and len(parsed["days"]) >= 5:
        parsed["generated_by"] = f"Google {MODEL_WORKOUT_GEN} (Feedback Refinement)"
        parsed["model_used"] = MODEL_WORKOUT_GEN
        return parsed

    fallback = _refine_smart_plan_fallback(current_plan, feedback_text, user_info)
    fallback["model_used"] = f"{MODEL_WORKOUT_GEN} (Simulated Refinement)"
    return fallback

# ==============================================================================
# SCENARIO 3: Nutrition & Recovery Tip Generator (Gemini Flash)
# ==============================================================================

def generate_nutrition_tip(goal: str, category: str = "nutrition", user_info: Optional[Dict[str, Any]] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Scenario 3:
    Uses Gemini Flash for rapid, low-latency generation of practical, evidence-based
    nutrition or recovery guidance complementing the user's training regimen.
    """
    system_instruction = (
        "You are FitBuddy Fast Nutrition & Recovery Coach powered by Gemini Flash. "
        "Provide quick, high-impact, evidence-based fitness advice. "
        "Output ONLY a valid JSON object."
    )

    prompt = f"""
Client Context:
- Target Fitness Goal: {goal}
- Topic Category: {category} (nutrition or recovery)
- Details: {user_info if user_info else 'General adult fitness'}

Generate a concise, scientifically accurate tip. Return strictly this JSON:
{{
  "tip_title": "Punchy Title (Max 7 words)",
  "category": "{category}",
  "tip_content": "A clear, actionable 2-3 sentence recommendation with practical numbers (e.g. grams of protein, hydration targets, sleep hours) that directly benefits the {goal} goal.",
  "action_step": "One immediate, practical action the user can implement today"
}}
"""

    raw_text = call_gemini(MODEL_NUTRITION_GEN, prompt, system_instruction, api_key=api_key)
    parsed = extract_json_from_text(raw_text) if raw_text else None

    if parsed and "tip_title" in parsed and "tip_content" in parsed:
        parsed["generated_by"] = f"Google {MODEL_NUTRITION_GEN}"
        parsed["model_used"] = MODEL_NUTRITION_GEN
        return parsed

    fallback = _generate_smart_tip_fallback(goal, category)
    fallback["generated_by"] = f"{MODEL_NUTRITION_GEN} (Simulated)"
    fallback["model_used"] = MODEL_NUTRITION_GEN
    return fallback

# ==============================================================================
# BUILT-IN SMART ENGINE (OFFLINE / FALLBACK SUPPORT)
# ==============================================================================

def _generate_smart_plan_fallback(name: str, age: int, weight: float, unit: str, goal: str, intensity: str, equipment: str, notes: str) -> Dict[str, Any]:
    goal_lower = goal.lower()
    intensity_lower = intensity.lower()

    if "weight" in goal_lower or "fat" in goal_lower or "loss" in goal_lower:
        plan_title = f"{intensity.capitalize()} Metabolic Burn & Fat Loss 7-Day Protocol"
        summary = f"Customized for {name} ({age}yo, {weight}{unit}), focused on high calorie expenditure, metabolic resistance circuits, and active recovery."
        overview = "Combines multi-joint compound resistance training with targeted HIIT and aerobic conditioning to accelerate caloric deficit while preserving lean muscle mass."
        focus = "Maximum caloric expenditure and lean metabolic tissue retention"
        recovery_tip = "Maintain a 300-500 kcal deficit. Prioritize 1.6-2.0g protein/kg body weight to prevent muscle catabolism during dieting."

        days = [
            {
                "day_number": 1,
                "day_name": "Day 1 - Monday",
                "focus": "Full Body Metabolic Circuit & Core",
                "warm_up": "6 mins dynamic warm-up: jumping jacks, inchworms, bodyweight squats",
                "duration_minutes": 50 if intensity_lower == "high" else 45,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Goblet Squats", "muscle_group": "Quads & Glutes", "sets": "4", "reps": "12-15", "rest": "45s", "coaching_tip": "Keep chest tall and sink hips below knee crease."},
                    {"name": "Dumbbell Push Press", "muscle_group": "Shoulders & Triceps", "sets": "3", "reps": "12", "rest": "45s", "coaching_tip": "Use a slight knee dip to drive weights smoothly overhead."},
                    {"name": "Romanian Deadlift", "muscle_group": "Hamstrings & Glutes", "sets": "3", "reps": "12", "rest": "60s", "coaching_tip": "Hinge at hips with neutral spine."},
                    {"name": "Mountain Climbers", "muscle_group": "Core & Cardio", "sets": "3", "reps": "40s", "rest": "30s", "coaching_tip": "Hold flat plank; drive knees rhythmically."}
                ],
                "cool_down": "5 mins static stretching: quad stretches, hamstring folds, child's pose"
            },
            {
                "day_number": 2,
                "day_name": "Day 2 - Tuesday",
                "focus": "HIIT Conditioning & Aerobic Intervals",
                "warm_up": "5 mins light jog in place, arm swings, high knees",
                "duration_minutes": 40,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Kettlebell / Dumbbell Swings", "muscle_group": "Posterior Chain", "sets": "4", "reps": "15", "rest": "45s", "coaching_tip": "Snap hips forward forcefully; do not squat the weight."},
                    {"name": "Bodyweight Step-Ups or Box Jumps", "muscle_group": "Legs & Explosive Power", "sets": "3", "reps": "12", "rest": "45s", "coaching_tip": "Land softly with knees slightly bent."},
                    {"name": "Plank Shoulder Taps", "muscle_group": "Core Anti-Rotation", "sets": "3", "reps": "20 taps", "rest": "30s", "coaching_tip": "Keep hips level without swaying."},
                    {"name": "Sprint / Rower Intervals", "muscle_group": "Cardiovascular", "sets": "6 rounds", "reps": "30s hard / 60s easy", "rest": "60s", "coaching_tip": "Aim for 85%+ heart rate peak during work bouts."}
                ],
                "cool_down": "6 mins deep hip flexor stretch, pigeon pose, diaphragmatic breathing"
            },
            {
                "day_number": 3,
                "day_name": "Day 3 - Wednesday",
                "focus": "Active Recovery, Mobility & Tissue Health",
                "warm_up": "5 mins cat-cow and spinal rotations",
                "duration_minutes": 30,
                "intensity_level": "low",
                "exercises": [
                    {"name": "Outdoor Aerobic Walk", "muscle_group": "Cardiovascular & Lymphatic", "sets": "1", "reps": "25 mins", "rest": "None", "coaching_tip": "Maintain conversational Zone 2 pace."},
                    {"name": "World's Greatest Stretch", "muscle_group": "Hips & Thoracic Spine", "sets": "2", "reps": "8 per side", "rest": "30s", "coaching_tip": "Breathe into tightness at end range."},
                    {"name": "Glute Bridges & Bird-Dogs", "muscle_group": "Glutes & Lower Back", "sets": "3", "reps": "12 reps", "rest": "30s", "coaching_tip": "Hold contraction 2s at apex."}
                ],
                "cool_down": "5 mins foam rolling quads, calves, and lats"
            },
            {
                "day_number": 4,
                "day_name": "Day 4 - Thursday",
                "focus": "Upper Body Density & Calorie Burn",
                "warm_up": "5 mins band pull-aparts, arm rotations",
                "duration_minutes": 45,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Push-Ups (or Incline Push-Ups)", "muscle_group": "Chest, Triceps, Core", "sets": "3", "reps": "12-15", "rest": "60s", "coaching_tip": "Full body tension from heels to neck."},
                    {"name": "Dumbbell Bent-Over Row", "muscle_group": "Upper Back & Lats", "sets": "4", "reps": "12", "rest": "60s", "coaching_tip": "Pull elbows toward pocket; squeeze scapulae."},
                    {"name": "Dumbbell Lateral Raises", "muscle_group": "Lateral Delts", "sets": "3", "reps": "15", "rest": "45s", "coaching_tip": "Lead with elbows; pause at shoulder height."},
                    {"name": "Jump Rope or Fast Rower Finisher", "muscle_group": "Conditioning", "sets": "4 rounds", "reps": "45s on / 45s off", "rest": "45s", "coaching_tip": "Maintain consistent tempo."}
                ],
                "cool_down": "5 mins chest door-frame and shoulder mobility"
            },
            {
                "day_number": 5,
                "day_name": "Day 5 - Friday",
                "focus": "Lower Body & Glute Power",
                "warm_up": "6 mins leg swings, bodyweight lunges",
                "duration_minutes": 45,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Dumbbell Walking Lunges", "muscle_group": "Quads & Glutes", "sets": "3", "reps": "12 per leg", "rest": "60s", "coaching_tip": "Keep front knee tracked over mid-foot."},
                    {"name": "Dumbbell Sumo Deadlift", "muscle_group": "Adductors & Hamstrings", "sets": "4", "reps": "12", "rest": "60s", "coaching_tip": "Wide stance, push knees out, hinge at hips."},
                    {"name": "Calf Raises & Wall-Sit Supersize", "muscle_group": "Lower Extremities", "sets": "3", "reps": "20 reps + 30s sit", "rest": "45s", "coaching_tip": "Full extension at the top of calf raises."}
                ],
                "cool_down": "5 mins figure-4 stretch and butterfly stretches"
            },
            {
                "day_number": 6,
                "day_name": "Day 6 - Saturday",
                "focus": "Aerobic Stamina & Abdominal Finishers",
                "warm_up": "5 mins light joint warm-up",
                "duration_minutes": 40,
                "intensity_level": "medium",
                "exercises": [
                    {"name": "Steady Incline Walking or Cycling", "muscle_group": "Cardiovascular Health", "sets": "1", "reps": "30 mins", "rest": "None", "coaching_tip": "Keep heart rate steady in Zone 2/3."},
                    {"name": "Hanging Knee Raises or Reverse Crunches", "muscle_group": "Lower Abdominals", "sets": "3", "reps": "15", "rest": "45s", "coaching_tip": "Curl pelvis toward chin; avoid momentum."},
                    {"name": "Side Plank Holds", "muscle_group": "Obliques", "sets": "3", "reps": "30s/side", "rest": "30s", "coaching_tip": "Keep torso aligned and hips lifted."}
                ],
                "cool_down": "5 mins spinal twist and cobra stretch"
            },
            {
                "day_number": 7,
                "day_name": "Day 7 - Sunday",
                "focus": "Total Rest & Nervous System Reset",
                "warm_up": "None",
                "duration_minutes": 15,
                "intensity_level": "low",
                "exercises": [
                    {"name": "Leisure Walk & Fresh Air", "muscle_group": "Full Body Relaxation", "sets": "1", "reps": "20 mins", "rest": "None", "coaching_tip": "Unwind and recharge for next week."},
                    {"name": "Diaphragmatic Breathing", "muscle_group": "Parasympathetic Reset", "sets": "1", "reps": "10 mins", "rest": "None", "coaching_tip": "Inhale 4s through nose, hold 4s, exhale 6s."}
                ],
                "cool_down": "Hydrate and prepare healthy meal prep for the week"
            }
        ]

    elif "muscle" in goal_lower or "hypertrophy" in goal_lower or "gain" in goal_lower or "strength" in goal_lower:
        plan_title = f"{intensity.capitalize()} Hypertrophy & Muscle Building Split"
        summary = f"Engineered for {name} ({age}yo, {weight}{unit}) to maximize mechanical tension, muscle protein synthesis, and systematic progressive overload."
        overview = "An Upper/Lower and Push/Pull hybrid split optimized for hypertrophy. Exercises are prioritized by biomechanical efficiency with regulated rest periods."
        focus = "Mechanical tension, progressive volume, and myofibrillar hypertrophy"
        recovery_tip = "Consume a 200-300 kcal surplus with 2.0g protein/kg body weight spaced across 4 meals to maximize 24-hour muscle protein synthesis."

        days = [
            {
                "day_number": 1,
                "day_name": "Day 1 - Monday",
                "focus": "Upper Body Strength (Chest & Back Foundation)",
                "warm_up": "6 mins shoulder circles, band pull-aparts, light push-ups",
                "duration_minutes": 50,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Barbell / Dumbbell Bench Press", "muscle_group": "Pectorals & Triceps", "sets": "4", "reps": "8-10", "rest": "90s", "coaching_tip": "Retract scapulae and press in a slight J-curve over sternum."},
                    {"name": "Bent-Over Dumbbell Row", "muscle_group": "Lats & Rhomboids", "sets": "4", "reps": "8-10", "rest": "90s", "coaching_tip": "Drive elbows toward hips; 1s peak contraction."},
                    {"name": "Incline Dumbbell Press", "muscle_group": "Upper Pectorals", "sets": "3", "reps": "10-12", "rest": "60s", "coaching_tip": "30-degree incline maximizes upper clavicular fiber recruitment."},
                    {"name": "Overhead Triceps Extension", "muscle_group": "Triceps Long Head", "sets": "3", "reps": "12-15", "rest": "60s", "coaching_tip": "Keep elbows pointed forward throughout."}
                ],
                "cool_down": "5 mins doorway chest stretch and lat hangs"
            },
            {
                "day_number": 2,
                "day_name": "Day 2 - Tuesday",
                "focus": "Lower Body Hypertrophy (Quad & Glute Emphasis)",
                "warm_up": "6 mins bodyweight squats, leg swings, glute bridges",
                "duration_minutes": 50,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Barbell / Dumbbell Squats", "muscle_group": "Quadriceps & Gluteus Maximus", "sets": "4", "reps": "8-10", "rest": "120s", "coaching_tip": "Brace core like receiving a punch; drive out of hole through midfoot."},
                    {"name": "Romanian Deadlift (RDL)", "muscle_group": "Hamstrings & Glutes", "sets": "4", "reps": "10", "rest": "90s", "coaching_tip": "Hinge backwards until hamstrings are fully loaded."},
                    {"name": "Bulgarian Split Squats", "muscle_group": "Single-Leg Quad & Glute", "sets": "3", "reps": "10/leg", "rest": "75s", "coaching_tip": "Slight forward torso angle shifts load onto working glute."},
                    {"name": "Standing Calf Raises", "muscle_group": "Gastrocnemius", "sets": "4", "reps": "15", "rest": "45s", "coaching_tip": "Pause 2s in the stretched bottom position."}
                ],
                "cool_down": "5 mins couch stretch for hip flexors and quad stretches"
            },
            {
                "day_number": 3,
                "day_name": "Day 3 - Wednesday",
                "focus": "Rest & Nutritional Recovery",
                "warm_up": "Light walking",
                "duration_minutes": 20,
                "intensity_level": "low",
                "exercises": [
                    {"name": "Active Recovery Walk", "muscle_group": "Circulation", "sets": "1", "reps": "25 mins", "rest": "None", "coaching_tip": "Stimulate blood flow to enhance nutrient delivery to repairing muscle."},
                    {"name": "Thoracic & Hip Mobility Drill", "muscle_group": "Connective Tissue", "sets": "2", "reps": "10 mins", "rest": "None", "coaching_tip": "Decompress spine and open anterior hip capsule."}
                ],
                "cool_down": "Hydrate and ensure high protein post-meal intake"
            },
            {
                "day_number": 4,
                "day_name": "Day 4 - Thursday",
                "focus": "Push Hypertrophy (Deltoids, Chest, Triceps)",
                "warm_up": "5 mins rotator cuff warm-up, arm swings",
                "duration_minutes": 50,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Overhead Dumbbell Shoulder Press", "muscle_group": "Anterior & Lateral Delts", "sets": "4", "reps": "8-10", "rest": "90s", "coaching_tip": "Lower dumbbells to chin level before pressing straight up."},
                    {"name": "Incline Dumbbell Flyes", "muscle_group": "Upper Pectorals", "sets": "3", "reps": "12", "rest": "60s", "coaching_tip": "Feel deep chest stretch; do not hyperextend shoulders."},
                    {"name": "Lateral Dumbbell Raises", "muscle_group": "Lateral Delts", "sets": "4", "reps": "12-15", "rest": "45s", "coaching_tip": "Lead with elbows; pause at top peak."},
                    {"name": "Cable Tricep Rope Pushdowns", "muscle_group": "Lateral Triceps Head", "sets": "3", "reps": "12", "rest": "45s", "coaching_tip": "Spread rope handles apart at bottom lockout."}
                ],
                "cool_down": "5 mins overhead triceps and pectoral stretch"
            },
            {
                "day_number": 5,
                "day_name": "Day 5 - Friday",
                "focus": "Pull Hypertrophy (Back, Rear Delts, Biceps)",
                "warm_up": "5 mins band pull-aparts and scapular pull-ups",
                "duration_minutes": 50,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Lat Pulldown or Pull-Ups", "muscle_group": "Latissimus Dorsi", "sets": "4", "reps": "8-10", "rest": "90s", "coaching_tip": "Pull elbows down into sides; arch upper thoracic spine."},
                    {"name": "Chest-Supported Row", "muscle_group": "Rhomboids & Mid-Traps", "sets": "3", "reps": "10-12", "rest": "75s", "coaching_tip": "Isolate upper back without swinging lower spine."},
                    {"name": "Face Pulls with External Rotation", "muscle_group": "Rear Delts & Rotator Cuff", "sets": "4", "reps": "15", "rest": "60s", "coaching_tip": "Pull thumbs towards ears; excellent posture builder."},
                    {"name": "Incline Dumbbell Bicep Curls", "muscle_group": "Biceps Long Head", "sets": "3", "reps": "12", "rest": "60s", "coaching_tip": "Pin elbows behind torso for maximum bicep stretch."}
                ],
                "cool_down": "5 mins bicep wall stretch and child's pose"
            },
            {
                "day_number": 6,
                "day_name": "Day 6 - Saturday",
                "focus": "Posterior Chain & Core Armory",
                "warm_up": "6 mins leg swings, hip circles, bodyweight lunges",
                "duration_minutes": 45,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Barbell / Dumbbell Hip Thrusts", "muscle_group": "Gluteus Maximus", "sets": "4", "reps": "10-12", "rest": "90s", "coaching_tip": "Tuck chin, squeeze glutes hard at horizontal top."},
                    {"name": "Hamstring Curls (Machine/Sliders)", "muscle_group": "Hamstrings", "sets": "3", "reps": "12-15", "rest": "60s", "coaching_tip": "3 seconds slow eccentric lowering."},
                    {"name": "Hanging Knee / Leg Raises", "muscle_group": "Rectus Abdominis", "sets": "3", "reps": "12", "rest": "45s", "coaching_tip": "Curl pelvis upwards; eliminate swinging momentum."},
                    {"name": "Farmer's Dumbbell Carries", "muscle_group": "Grip & Core Anti-Flexion", "sets": "3", "reps": "40 meters", "rest": "60s", "coaching_tip": "Stand tall with ribs locked down."}
                ],
                "cool_down": "5 mins hamstring stretch and lower back decompression"
            },
            {
                "day_number": 7,
                "day_name": "Day 7 - Sunday",
                "focus": "Complete Rest & Muscle Repair",
                "warm_up": "Rest",
                "duration_minutes": 0,
                "intensity_level": "low",
                "exercises": [
                    {"name": "8+ Hours Sleep & Re-feed", "muscle_group": "Systemic Recovery", "sets": "1", "reps": "Full Day", "rest": "Full", "coaching_tip": "Deep sleep triggers growth hormone and cellular repair."},
                    {"name": "Gentle Mobility & Hydration", "muscle_group": "Full Body Relaxation", "sets": "1", "reps": "15 mins", "rest": "None", "coaching_tip": "Drink water with electrolytes and plan weekly meals."}
                ],
                "cool_down": "Mentally prepare for next week's progressive overload"
            }
        ]

    else:
        # General Wellness
        plan_title = f"{intensity.capitalize()} Total Body Wellness & Functional Vitality"
        summary = f"Crafted for {name} ({age}yo, {weight}{unit}) to enhance longevity, functional mobility, cardiovascular health, and balanced joint strength."
        overview = "A holistic 7-day routine balancing aerobic conditioning, joint mobility, muscular endurance, and autonomic nervous system recovery."
        focus = "Cardiorespiratory longevity, functional mobility, and daily vitality"
        recovery_tip = "Stay hydrated with 2.5-3 liters of water daily. Prioritize 7-8 hours of quality sleep to maintain hormonal and mental balance."

        days = [
            {
                "day_number": 1,
                "day_name": "Day 1 - Monday",
                "focus": "Functional Total Body Strength",
                "warm_up": "5 mins arm circles, torso twists, bodyweight squats",
                "duration_minutes": 40,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Goblet Squats", "muscle_group": "Quads & Core", "sets": "3", "reps": "12", "rest": "60s", "coaching_tip": "Keep feet flat and torso upright."},
                    {"name": "Push-Ups (or Kneeling)", "muscle_group": "Chest & Core", "sets": "3", "reps": "10", "rest": "60s", "coaching_tip": "Engage core to protect lower back."},
                    {"name": "Dumbbell Rows", "muscle_group": "Upper Back", "sets": "3", "reps": "12", "rest": "60s", "coaching_tip": "Keep back flat and pull elbow past torso."},
                    {"name": "Plank Hold", "muscle_group": "Core", "sets": "3", "reps": "45s", "rest": "45s", "coaching_tip": "Breathe steadily while squeezing glutes."}
                ],
                "cool_down": "5 mins full body stretch"
            },
            {
                "day_number": 2,
                "day_name": "Day 2 - Tuesday",
                "focus": "Aerobic Stamina & Joint Health",
                "warm_up": "5 mins light joint warm-up",
                "duration_minutes": 35,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Zone 2 Jogging, Cycling, or Incline Walk", "muscle_group": "Cardiovascular", "sets": "1", "reps": "25 mins", "rest": "None", "coaching_tip": "Maintain conversational breathing pace."},
                    {"name": "Bird-Dog Extensions", "muscle_group": "Core & Spinal Stabilizers", "sets": "3", "reps": "10/side", "rest": "30s", "coaching_tip": "Reach opposite arm and leg straight out."},
                    {"name": "Glute Bridges", "muscle_group": "Glutes", "sets": "3", "reps": "15", "rest": "30s", "coaching_tip": "Squeeze glutes at the top for 2 seconds."}
                ],
                "cool_down": "5 mins calf and hamstring stretch"
            },
            {
                "day_number": 3,
                "day_name": "Day 3 - Wednesday",
                "focus": "Yoga Flow & Joint Mobility",
                "warm_up": "3 mins child's pose and breathing",
                "duration_minutes": 30,
                "intensity_level": "low",
                "exercises": [
                    {"name": "Sun Salutation Sequence", "muscle_group": "Full Body Mobility", "sets": "4 rounds", "reps": "Smooth flow", "rest": "30s", "coaching_tip": "Match movements with deep breathing."},
                    {"name": "Warrior II into Side Angle", "muscle_group": "Hips & Spine", "sets": "3", "reps": "45s/side", "rest": "30s", "coaching_tip": "Keep shoulders relaxed away from ears."},
                    {"name": "Seated Forward Fold & Twist", "muscle_group": "Hamstrings & Spine", "sets": "2", "reps": "1 min", "rest": "30s", "coaching_tip": "Lengthen spine before folding."}
                ],
                "cool_down": "5 mins Savasana meditation"
            },
            {
                "day_number": 4,
                "day_name": "Day 4 - Thursday",
                "focus": "Core Stability & Balance",
                "warm_up": "5 mins hip openers and arm circles",
                "duration_minutes": 35,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Single-Leg RDL (Bodyweight/Light DB)", "muscle_group": "Balance & Hamstrings", "sets": "3", "reps": "10/leg", "rest": "45s", "coaching_tip": "Hinge at hip while keeping hips square."},
                    {"name": "Dead Bugs", "muscle_group": "Deep Abdominal Core", "sets": "3", "reps": "12/side", "rest": "45s", "coaching_tip": "Press lower back firmly into floor."},
                    {"name": "Step-Ups onto Bench", "muscle_group": "Quads & Glutes", "sets": "3", "reps": "12/leg", "rest": "45s", "coaching_tip": "Drive through the heel of elevated foot."},
                    {"name": "Side Plank Hip Lifts", "muscle_group": "Obliques", "sets": "3", "reps": "10/side", "rest": "30s", "coaching_tip": "Lift hips toward ceiling with control."}
                ],
                "cool_down": "5 mins quad and hip flexor stretches"
            },
            {
                "day_number": 5,
                "day_name": "Day 5 - Friday",
                "focus": "Resistance Training & Posture",
                "warm_up": "5 mins dynamic arm and leg stretches",
                "duration_minutes": 40,
                "intensity_level": intensity,
                "exercises": [
                    {"name": "Dumbbell Overhead Press", "muscle_group": "Shoulders & Core", "sets": "3", "reps": "10-12", "rest": "60s", "coaching_tip": "Do not arch lower back; keep glutes engaged."},
                    {"name": "Dumbbell Romanian Deadlift", "muscle_group": "Hamstrings & Glutes", "sets": "3", "reps": "12", "rest": "60s", "coaching_tip": "Hinge hips back while keeping weights close."},
                    {"name": "Band Pull-Aparts & Rows", "muscle_group": "Upper Back & Posture", "sets": "3", "reps": "15", "rest": "45s", "coaching_tip": "Squeeze shoulder blades together firmly."},
                    {"name": "Wall Sit Hold", "muscle_group": "Quad Endurance", "sets": "3", "reps": "45s", "rest": "45s", "coaching_tip": "Keep thighs parallel to the floor."}
                ],
                "cool_down": "5 mins upper back and chest opener"
            },
            {
                "day_number": 6,
                "day_name": "Day 6 - Saturday",
                "focus": "Recreational Outdoor Conditioning",
                "warm_up": "5 mins light walking",
                "duration_minutes": 45,
                "intensity_level": "medium",
                "exercises": [
                    {"name": "Outdoor Hike, Cycling, or Swimming", "muscle_group": "Aerobic Health", "sets": "1", "reps": "40 mins", "rest": "None", "coaching_tip": "Enjoy the outdoor environment and keep moving."},
                    {"name": "Dynamic Calf & Ankle Mobility", "muscle_group": "Lower Extremities", "sets": "2", "reps": "10 each", "rest": "30s", "coaching_tip": "Enhance ankle dorsiflexion for healthier gait."}
                ],
                "cool_down": "5 mins deep breathing and calf stretching"
            },
            {
                "day_number": 7,
                "day_name": "Day 7 - Sunday",
                "focus": "Rest, Mindful Recovery & Nutrition Prep",
                "warm_up": "None",
                "duration_minutes": 15,
                "intensity_level": "low",
                "exercises": [
                    {"name": "Mindful Meditation & Relaxation", "muscle_group": "Nervous System", "sets": "1", "reps": "15 mins", "rest": "Full", "coaching_tip": "Focus on natural breath rhythm to lower cortisol."},
                    {"name": "Weekly Meal Preparation", "muscle_group": "Nutritional Base", "sets": "1", "reps": "1 hr", "rest": "None", "coaching_tip": "Prep colorful vegetables, lean protein, and complex carbs."}
                ],
                "cool_down": "Rest and recover for the week ahead"
            }
        ]

    return {
        "title": plan_title,
        "summary": summary,
        "overview": overview,
        "weekly_goal_focus": focus,
        "general_recovery_tip": recovery_tip,
        "days": days,
        "generated_by": "FitBuddy Smart Engine"
    }

def _refine_smart_plan_fallback(current_plan: Dict[str, Any], feedback_text: str, user_info: Dict[str, Any]) -> Dict[str, Any]:
    fb_lower = feedback_text.lower()
    updated_plan = json.loads(json.dumps(current_plan.get("plan_data", current_plan)))
    days = updated_plan.get("days", [])
    changes = []

    if "cardio" in fb_lower or "running" in fb_lower or "stamina" in fb_lower:
        changes.append("amplified cardiovascular conditioning and high-intensity intervals")
        for day in days:
            if day.get("day_number") in [2, 4]:
                day["focus"] = f"{day.get('focus', '')} + High-Intensity Cardio Burn"
                day["exercises"].append({
                    "name": "Interval Sprints / Rower Sprints",
                    "muscle_group": "Cardiovascular & Aerobic Capacity",
                    "sets": "5 rounds",
                    "reps": "30s max effort / 60s recovery",
                    "rest": "60s",
                    "coaching_tip": "Push heart rate into high aerobic zone during intervals."
                })

    if "rest" in fb_lower or "tired" in fb_lower or "recovery" in fb_lower:
        changes.append("incorporated dedicated active recovery and restorative mobility days")
        for day in days:
            if day.get("day_number") == 3 and "Rest" not in day.get("focus", ""):
                day["focus"] = "Deep Rest, Mobility & Nervous System Recovery"
                day["intensity_level"] = "low"
                day["duration_minutes"] = 25
                day["exercises"] = [
                    {"name": "Gentle Walking & Hydration", "muscle_group": "Full Body", "sets": "1", "reps": "20 mins", "rest": "None", "coaching_tip": "Keep heart rate low and relax."},
                    {"name": "Foam Rolling & Full Body Static Stretch", "muscle_group": "Myofascial Tissue", "sets": "1", "reps": "15 mins", "rest": "None", "coaching_tip": "Hold each stretch for 30-45 seconds."}
                ]
            elif day.get("day_number") == 6 and len(changes) < 2:
                day["focus"] = "Active Recovery & Restorative Mobility"
                day["intensity_level"] = "low"
                day["duration_minutes"] = 25

    if "back" in fb_lower or "pain" in fb_lower or "injury" in fb_lower or "squat" in fb_lower:
        changes.append("substituted compressive spinal loads with spine-friendly hip and quad alternatives")
        for day in days:
            for ex in day.get("exercises", []):
                if "deadlift" in ex.get("name", "").lower() or "barbell squat" in ex.get("name", "").lower():
                    ex["name"] = "Spine-Supported Hip Thrust / Glute Bridge"
                    ex["coaching_tip"] = "Safely trains glutes and hamstrings without compressive axial load on lumbar spine."

    if "short" in fb_lower or "30 min" in fb_lower or "time" in fb_lower:
        changes.append("streamlined sessions into dense 30-minute high-efficiency workouts")
        for day in days:
            day["duration_minutes"] = 30
            if len(day.get("exercises", [])) > 3:
                day["exercises"] = day["exercises"][:3]

    if "core" in fb_lower or "abs" in fb_lower:
        changes.append("added targeted core stabilization and abdominal conditioning")
        for day in days:
            if day.get("day_number") in [1, 5]:
                day["exercises"].append({
                    "name": "Hanging Knee Raises & Plank Combo",
                    "muscle_group": "Rectus Abdominis & Transverse Abdominis",
                    "sets": "3",
                    "reps": "15 reps + 45s plank",
                    "rest": "45s",
                    "coaching_tip": "Keep pelvis tucked and core engaged throughout."
                })

    if not changes:
        changes.append(f"customized routine according to: '{feedback_text}'")

    updated_plan["title"] = f"Refined: {updated_plan.get('title', '7-Day Plan')}"
    updated_plan["summary"] = f"Updated based on your feedback: {', '.join(changes)}. Retains balanced progressive fitness progression."
    updated_plan["generated_by"] = "FitBuddy Smart Engine (Feedback Refined)"

    return updated_plan

def _generate_smart_tip_fallback(goal: str, category: str) -> Dict[str, Any]:
    g = goal.lower()
    c = category.lower()

    if "muscle" in g or "gain" in g or "hypertrophy" in g:
        if c == "recovery":
            return {
                "tip_title": "Sleep-Driven Growth Hormone Optimization",
                "category": "recovery",
                "tip_content": "Deep slow-wave sleep (stages 3 & 4) triggers peak release of human growth hormone (HGH) essential for repairing torn muscle fibers. Aim for 7.5 to 9 hours of uninterrupted sleep in a cool (65-68°F / 18-20°C) room.",
                "action_step": "Power down screens 45 minutes before bed and take 300mg of magnesium glycinate to support neuromuscular recovery."
            }
        else:
            return {
                "tip_title": "Post-Workout Protein & Glycogen Window",
                "category": "nutrition",
                "tip_content": "Consume 25-35 grams of high-quality protein combined with 40-50 grams of fast-digesting carbohydrates within 90 minutes post-workout. This halts muscle catabolism and rapidly replenishes depleted glycogen stores.",
                "action_step": "Drink a shake with 1 scoop of whey or plant protein and a ripe banana immediately following your resistance training session."
            }

    elif "weight" in g or "loss" in g or "fat" in g:
        if c == "recovery":
            return {
                "tip_title": "Manage Cortisol to Prevent Fat Retention",
                "category": "recovery",
                "tip_content": "Chronic stress elevates cortisol, which signals the body to store visceral belly fat and increases appetite for sugary foods. Contrast showers and 10 minutes of diaphragmatic nasal breathing reduce sympathetic nervous system tone.",
                "action_step": "Dedicate 10 minutes post-workout to calm walking or lying down with feet elevated to trigger parasympathetic fat-burning mode."
            }
        else:
            return {
                "tip_title": "Front-Load Protein & High-Volume Veggies",
                "category": "nutrition",
                "tip_content": "Target 1.6 to 2.2 grams of protein per kilogram of body weight while in a calorie deficit. High protein has the highest thermic effect of food (TEF) and preserves lean metabolically active tissue while keeping satiety hormones high.",
                "action_step": "Fill half of your lunch and dinner plates with non-starchy cruciferous vegetables (broccoli, spinach, cauliflower) before adding proteins and carbs."
            }

    else:
        # General Wellness
        if c == "recovery":
            return {
                "tip_title": "Electrolyte Hydration & Cellular Rejuvenation",
                "category": "recovery",
                "tip_content": "Muscle stiffness and sluggishness are frequently caused by mild intracellular dehydration. Drink 35ml of water per kg of body weight daily, adding a pinch of unrefined sea salt or an electrolyte packet during intense workouts.",
                "action_step": "Drink a 500ml glass of water with a pinch of sea salt and lemon juice immediately upon waking."
            }
        else:
            return {
                "tip_title": "The 80/20 Whole-Food Longevity Rule",
                "category": "nutrition",
                "tip_content": "Anchor 80% of your daily nutrition around minimally processed single-ingredient foods (wild fish, eggs, quinoa, berries, leafy greens, avocados) and allow 20% flexibility for enjoyable social eating.",
                "action_step": "Aim to eat at least 3 distinct naturally colorful plant foods (greens, reds, purples) with each meal to feed diverse gut microbiota."
            }

# ==============================================================================
# ENHANCEMENT: Personalized Meal Planning Engine (Gemini Flash)
# ==============================================================================

def generate_meal_plan(goal: str, diet_preference: str = "omnivore", calories_target: int = 2200, language: str = "en", api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Generates a structured daily meal plan (Breakfast, Lunch, Snack, Dinner)
    calibrated to goal, diet preference, and caloric targets.
    Supports English ('en') and Tamil ('ta').
    """
    lang_str = "Tamil (தமிழ்)" if language == "ta" else "English"
    system_instruction = (
        f"You are FitBuddy AI Nutritionist. Create a healthy, delicious daily meal plan in {lang_str}. "
        "Output ONLY a valid JSON object matching the requested schema."
    )

    prompt = f"""
Create a daily meal plan for:
- Fitness Goal: {goal}
- Dietary Preference: {diet_preference} (e.g. omnivore, vegetarian, vegan, high-protein, keto)
- Target Daily Calories: ~{calories_target} kcal
- Language: {lang_str}

Return strictly this JSON format:
{{
  "title": "Daily Meal Plan for {goal.title()}",
  "total_calories": {calories_target},
  "macros": {{
    "protein": "140g",
    "carbs": "220g",
    "fats": "65g"
  }},
  "meals": [
    {{
      "meal_name": "Breakfast",
      "items": "E.g. Scrambled eggs or oats with berries",
      "calories": 450,
      "protein_grams": 30,
      "benefits": "Provides sustained morning energy and essential amino acids"
    }},
    {{
      "meal_name": "Lunch",
      "items": "...",
      "calories": 650,
      "protein_grams": 45,
      "benefits": "..."
    }},
    {{
      "meal_name": "Afternoon Snack",
      "items": "...",
      "calories": 300,
      "protein_grams": 20,
      "benefits": "..."
    }},
    {{
      "meal_name": "Dinner",
      "items": "...",
      "calories": 600,
      "protein_grams": 40,
      "benefits": "..."
    }}
  ],
  "hydration_target": "3.0 Liters water daily",
  "chef_tip": "Practical meal prep advice"
}}
"""
    raw = call_gemini(MODEL_NUTRITION_GEN, prompt, system_instruction, api_key=api_key)
    parsed = extract_json_from_text(raw) if raw else None

    if parsed and "meals" in parsed:
        parsed["generated_by"] = f"Google {MODEL_NUTRITION_GEN}"
        parsed["language"] = language
        return parsed

    # Smart fallback meal plan
    return _generate_smart_meal_plan_fallback(goal, diet_preference, calories_target, language)

def _generate_smart_meal_plan_fallback(goal: str, diet: str, calories: int, language: str) -> Dict[str, Any]:
    is_tamil = language == "ta"
    is_veg = "veg" in diet.lower()

    if is_tamil:
        title = "தினசரி ஊட்டச்சத்து மற்றும் உணவுத் திட்டம்"
        b_name, b_items = "காலை உணவு (Breakfast)", "முளைகட்டிய பயறு சாலட் மற்றும் அவல்/ஓட்ஸ் கஞ்சி அல்லது 3 முட்டை ஆம்லெட்" if not is_veg else "முளைகட்டிய பயறு, ராகி தோசை 2, சாம்பார் மற்றும் நட்ஸ்"
        l_name, l_items = "மதிய உணவு (Lunch)", "சிவப்பரிசி சாதம், கீரை கூட்டு, கொண்டைக்கடலை அல்லது சிக்கன் கறி (150g), வெள்ளரி சாலட்" if not is_veg else "குதிரைவாலி சாதம், கொண்டைக்கடலை சுண்டல், கீரை பொரியல், கெட்டித் தயிர்"
        s_name, s_items = "மாலை சிற்றுண்டி (Snack)", "வறுத்த கடலை (Roasted Chana) மற்றும் க்ரீன் டீ அல்லது பாதாம் பால்"
        d_name, d_items = "இரவு உணவு (Dinner)", "கோதுமை சப்பாத்தி 2, பன்னீர் அல்லது மீன் பொரியல், சுரைக்காய் கூட்டு" if not is_veg else "கோதுமை சப்பாத்தி 2, பன்னீர் புர்ஜி, பாசிப்பருப்பு தால்"
        hyd = "3.2 லிட்டர் தண்ணீர் தினசரி குடிக்கவும்"
        tip = "உணவை மெதுவாக மென்று சாப்பிடுங்கள், இரவு 8 மணிக்குள் உணவை முடிக்கவும்."
    else:
        title = f"Balanced {diet.capitalize()} Daily Meal Protocol for {goal.title()}"
        b_name, b_items = "Breakfast", "Oatmeal with chia seeds, whey or soy protein scoop, and blueberries" if is_veg else "3 whole eggs scrambled with spinach, 1 slice whole grain toast, and avocado"
        l_name, l_items = "Lunch", "Quinoa bowl with roasted chickpeas, steamed broccoli, and tahini dressing" if is_veg else "Grilled chicken breast (180g), brown rice, grilled asparagus, and olive oil drizzle"
        s_name, s_items = "Afternoon Power Snack", "Greek yogurt with pumpkin seeds and a green apple" if not is_veg else "Handful of roasted almonds and a scoop of plant protein shake"
        d_name, d_items = "Dinner", "Grilled paneer / tofu tikka with roasted sweet potato and mixed greens" if is_veg else "Wild baked salmon fillet, quinoa, and sautéed garlic green beans"
        hyd = "3.0 Liters of water throughout the day"
        tip = "Prepare your proteins in batches on Sunday to ensure consistent nutrition throughout busy weekdays."

    return {
        "title": title,
        "total_calories": calories,
        "macros": {
            "protein": f"{int(calories * 0.28 / 4)}g",
            "carbs": f"{int(calories * 0.45 / 4)}g",
            "fats": f"{int(calories * 0.27 / 9)}g"
        },
        "meals": [
            {"meal_name": b_name, "items": b_items, "calories": int(calories * 0.25), "protein_grams": 28, "benefits": "Sustained glucose delivery and muscle preservation."},
            {"meal_name": l_name, "items": l_items, "calories": int(calories * 0.35), "protein_grams": 42, "benefits": "High micronutrient density and steady afternoon energy."},
            {"meal_name": s_name, "items": s_items, "calories": int(calories * 0.15), "protein_grams": 18, "benefits": "Prevents late-afternoon metabolic crash."},
            {"meal_name": d_name, "items": d_items, "calories": int(calories * 0.25), "protein_grams": 35, "benefits": "Low glycemic recovery meal supporting sleep."}
        ],
        "hydration_target": hyd,
        "chef_tip": tip,
        "language": language,
        "generated_by": "FitBuddy Smart Nutritionist"
    }

# ==============================================================================
# ENHANCEMENT: AI Voice Assistant & Advanced Coach (Gemini 1.5 Pro / Flash)
# ==============================================================================

def ask_fitness_coach(query: str, context: Optional[str] = None, language: str = "en", api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Answers spoken or typed user questions about exercise form, nutrition,
    recovery, and physiology in 2-3 spoken sentences.
    Supports English ('en') and Tamil ('ta').
    """
    is_tamil = language == "ta"
    lang_instruction = "Respond in fluent, encouraging Tamil (தமிழ்)." if is_tamil else "Respond in encouraging, clear English."

    system_instruction = (
        "You are FitBuddy AI Personal Coach. You provide voice-ready, concise, evidence-based fitness advice. "
        "Keep your response strictly to 2-3 spoken sentences so it sounds natural when read aloud by text-to-speech. "
        f"{lang_instruction}"
    )

    prompt = f"""
User Query: "{query}"
Client Context: {context if context else 'Active adult seeking fitness guidance'}

Provide an accurate, motivating 2-3 sentence answer suitable for voice readout:
"""
    raw = call_gemini(MODEL_NUTRITION_GEN, prompt, system_instruction, api_key=api_key)
    if raw and raw.strip():
        return {
            "query": query,
            "response": raw.strip(),
            "language": language,
            "voice_ready": True,
            "model_used": MODEL_NUTRITION_GEN
        }

    # Intelligent fallback responses
    q_low = query.lower()
    if is_tamil:
        if "protein" in q_low or "புரதம்" in q_low:
            resp = "தசை வளர்ச்சிக்கு உங்கள் உடல் எடையில் ஒவ்வொரு கிலோவிற்கும் 1.6 முதல் 2.0 கிராம் புரதம் தேவை. முட்டை, கொண்டைக்கடலை, பன்னீர் மற்றும் பருப்பு வகைகள் சிறந்த புரத ஆதாரங்கள் ஆகும்."
        elif "water" in q_low or "தண்ணீர்" in q_low:
            resp = "தினசரி குறைந்தது 3 முதல் 3.5 லிட்டர் தண்ணீர் குடிப்பது தசை சோர்வை தடுத்து ஆற்றலை அதிகரிக்கும். உடற்பயிற்சிக்கு முன்னும் பின்னும் ஒரு டம்ளர் தண்ணீர் குடிக்க மறக்காதீர்கள்."
        else:
            resp = "நிலையான தொடர் பயிற்சியும், சரியான தூக்கமும் உங்கள் உடற்பயிற்சி இலக்குகளை எளிதாக அடைய உதவும். தொடர்ந்து உடற்பயிற்சி செய்யுங்கள், உங்கள் முன்னேற்றம் மிக அருகில் உள்ளது!"
    else:
        if "protein" in q_low:
            resp = "For optimal muscle recovery, aim for 1.6 to 2.2 grams of protein per kilogram of body weight spread across your meals. Eggs, Greek yogurt, chicken, lentils, and protein shakes are fantastic options."
        elif "water" in q_low or "hydrate" in q_low:
            resp = "Drink at least 3 to 3.5 liters of water daily, adding electrolytes during hard sessions. Proper hydration improves exercise endurance by up to fifteen percent!"
        elif "squat" in q_low or "knee" in q_low:
            resp = "When squatting, screw your feet into the floor to keep knees tracking over your midfoot. Avoid letting knees cave inward and hinge through your hips for maximum power."
        else:
            resp = "Consistency beats intensity every single time. Focus on progressive overload, prioritize seven to eight hours of sleep, and you will see steady results!"

    return {
        "query": query,
        "response": resp,
        "language": language,
        "voice_ready": True,
        "model_used": f"{MODEL_NUTRITION_GEN} (Simulated)"
    }

