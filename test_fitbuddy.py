import os
import unittest
import json

# Ensure test DB is isolated
os.environ["FITBUDDY_DB"] = "test_fitbuddy.db"
os.environ["DATABASE_URL"] = "sqlite:///./test_fitbuddy.db"

import database
import gemini_service

class FitBuddyComprehensiveTestSuite(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize test SQLite database
        database.init_db()

    @classmethod
    def tearDownClass(cls):
        # Clean up test database file
        if os.path.exists("test_fitbuddy.db"):
            try:
                os.remove("test_fitbuddy.db")
            except Exception:
                pass

    def test_01_scenario1_gemini_pro_workout_generation(self):
        """Scenario 1: User personal details -> 7-day workout plan using Gemini 1.5 Pro."""
        name = "Jordan Lee"
        age = 29
        weight = 75.0
        unit = "kg"
        goal = "weight loss"
        intensity = "medium"
        equipment = "full gym"
        notes = "No lower back injuries"

        # 1. Save user to SQLite
        user_id = database.save_user(name, age, weight, goal, intensity, equipment, unit, notes)
        self.assertIsNotNone(user_id)
        self.assertGreater(user_id, 0)

        # 2. Generate 7-day workout plan
        plan = gemini_service.generate_workout_plan(
            name=name, age=age, weight=weight, weight_unit=unit,
            goal=goal, intensity=intensity, equipment=equipment, notes=notes
        )

        self.assertIn("title", plan)
        self.assertIn("days", plan)
        self.assertEqual(len(plan["days"]), 7, "Plan must contain exactly 7 days")
        self.assertIn("gemini", plan.get("model_used", "").lower())

        # Verify Day structure
        first_day = plan["days"][0]
        self.assertIn("day_number", first_day)
        self.assertIn("focus", first_day)
        self.assertIn("warm_up", first_day)
        self.assertIn("exercises", first_day)
        self.assertGreaterEqual(len(first_day["exercises"]), 1)
        self.assertIn("cool_down", first_day)

        # 3. Save plan in SQLite
        plan_id = database.save_workout_plan(
            user_id=user_id,
            title=plan["title"],
            summary=plan.get("summary", ""),
            goal=goal,
            intensity=intensity,
            plan_data=plan,
            version=1,
            model_used=plan.get("model_used", "gemini-1.5-pro")
        )
        self.assertGreater(plan_id, 0)

        # 4. Verify retrieval from SQLite
        retrieved_plan = database.get_workout_plan(plan_id)
        self.assertIsNotNone(retrieved_plan)
        self.assertEqual(retrieved_plan["user_id"], user_id)
        self.assertEqual(retrieved_plan["version"], 1)
        self.assertEqual(len(retrieved_plan["plan_data"]["days"]), 7)

    def test_02_scenario2_gemini_pro_feedback_regeneration(self):
        """Scenario 2: Feedback loop on existing plan -> regenerated plan with version tracking using Gemini 1.5 Pro."""
        name = "Sam Taylor"
        user_id = database.save_user(name, 32, 80.0, "muscle gain", "high", "dumbbells", "kg", "Slight shoulder tightness")
        
        # Initial Plan
        initial_plan = gemini_service.generate_workout_plan(name, 32, 80.0, "kg", "muscle gain", "high", "dumbbells")
        plan_id = database.save_workout_plan(user_id, "Initial Split", "Initial summary", "muscle gain", "high", initial_plan, version=1)

        # User provides feedback
        feedback_text = "more focus on cardio and include more rest days"
        feedback_id = database.save_plan_feedback(plan_id, feedback_text)
        self.assertGreater(feedback_id, 0)

        # Regenerate updated plan
        user_info = database.get_user(user_id)
        updated_plan = gemini_service.regenerate_workout_plan_with_feedback(
            current_plan=initial_plan,
            feedback_text=feedback_text,
            user_info=user_info
        )

        self.assertIn("title", updated_plan)
        self.assertIn("days", updated_plan)
        self.assertEqual(len(updated_plan["days"]), 7)
        self.assertIn("gemini", updated_plan.get("model_used", "").lower())

        # Save as Version 2
        v2_plan_id = database.save_workout_plan(
            user_id=user_id,
            title=updated_plan["title"],
            summary=updated_plan.get("summary", ""),
            goal="muscle gain",
            intensity="high",
            plan_data=updated_plan,
            version=2,
            model_used=updated_plan.get("model_used", "gemini-1.5-pro")
        )

        # Check version history
        history = database.get_user_plan_history(user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["version"], 2)
        self.assertEqual(history[1]["version"], 1)

        # Check feedback log
        feedbacks = database.get_plan_feedback_history(plan_id)
        self.assertEqual(len(feedbacks), 1)
        self.assertEqual(feedbacks[0]["feedback_text"], feedback_text)

    def test_03_scenario3_gemini_flash_nutrition_and_recovery_tips(self):
        """Scenario 3: Goal-targeted nutrition and recovery tips with Gemini Flash."""
        # Test Nutrition tip for muscle gain
        tip1 = gemini_service.generate_nutrition_tip(goal="muscle gain", category="nutrition")
        self.assertIn("tip_title", tip1)
        self.assertIn("tip_content", tip1)
        self.assertIn("action_step", tip1)
        self.assertIn("gemini", tip1.get("model_used", "").lower())

        # Test Recovery tip for weight loss
        tip2 = gemini_service.generate_nutrition_tip(goal="weight loss", category="recovery")
        self.assertIn("tip_title", tip2)
        self.assertIn("tip_content", tip2)
        self.assertIn("action_step", tip2)

        # Save tips in SQLite
        tip_id1 = database.save_nutrition_tip("muscle gain", tip1["tip_title"], tip1["tip_content"], tip1["action_step"], "nutrition", model_used=tip1.get("model_used", "gemini-1.5-flash"))
        tip_id2 = database.save_nutrition_tip("weight loss", tip2["tip_title"], tip2["tip_content"], tip2["action_step"], "recovery", model_used=tip2.get("model_used", "gemini-1.5-flash"))

        self.assertGreater(tip_id1, 0)
        self.assertGreater(tip_id2, 0)

        # Verify recent tips query
        recent_tips = database.get_recent_tips(limit=5)
        self.assertGreaterEqual(len(recent_tips), 2)

    def test_04_admin_dashboard_and_crud(self):
        """Admin Dashboard & User CRUD Operations."""
        # 1. Fetch admin statistics
        stats = database.get_admin_statistics()
        self.assertIn("total_users", stats)
        self.assertIn("total_plans", stats)
        self.assertIn("total_feedbacks", stats)
        self.assertIn("total_tips", stats)
        self.assertGreaterEqual(stats["total_users"], 2)
        self.assertGreaterEqual(stats["total_plans"], 3)

        # 2. Test user deletion CRUD
        temp_user_id = database.save_user("Temp Delete Test", 25, 65.0, "general wellness", "low")
        self.assertIsNotNone(database.get_user(temp_user_id))
        
        delete_success = database.delete_user(temp_user_id)
        self.assertTrue(delete_success)
        self.assertIsNone(database.get_user(temp_user_id))

    def test_05_meal_planning_and_coach_tamil_english(self):
        """Future Enhancements: Meal Planning, Voice Coach, Multi-Language, and Biometrics Progress."""
        # 1. Meal Planning in English
        meal_en = gemini_service.generate_meal_plan("weight loss", "vegetarian", 1800, language="en")
        self.assertIn("meals", meal_en)
        self.assertEqual(len(meal_en["meals"]), 4)
        self.assertIn("protein", meal_en["macros"])

        # 2. Meal Planning in Tamil
        meal_ta = gemini_service.generate_meal_plan("muscle gain", "omnivore", 2400, language="ta")
        self.assertIn("meals", meal_ta)
        self.assertEqual(meal_ta["language"], "ta")

        # 3. Save meal plan in SQLite
        mid = database.save_meal_plan("muscle gain", "omnivore", 2400, meal_ta, language="ta")
        self.assertGreater(mid, 0)
        saved_meals = database.get_user_meal_plans()
        self.assertGreaterEqual(len(saved_meals), 1)

        # 4. AI Coach in English and Tamil
        coach_en = gemini_service.ask_fitness_coach("What to eat after a heavy squat session?", language="en")
        self.assertIn("response", coach_en)
        self.assertTrue(coach_en["voice_ready"])

        coach_ta = gemini_service.ask_fitness_coach("தசை வளர்ச்சிக்கு என்ன சாப்பிட வேண்டும்?", language="ta")
        self.assertIn("response", coach_ta)
        self.assertEqual(coach_ta["language"], "ta")

        # 5. Progress Logging (Biometrics & Wearables)
        user_id = database.save_user("Biometric User", 26, 70.0, "muscle gain", "high")
        pid = database.save_progress_log(user_id, "2026-10-03", 70.0, workouts_completed=1, calories_burned=520, steps=9200)
        self.assertGreater(pid, 0)

        logs = database.get_user_progress_logs(user_id)
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["steps"], 9200)

if __name__ == "__main__":
    unittest.main()
