import os
import json
import mimetypes
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import database
import gemini_service

PORT = int(os.environ.get("PORT", 8000))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

class FitBuddyHandler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-gemini-api-key")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def _read_json_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            if content_length > 0:
                raw = self.rfile.read(content_length).decode("utf-8")
                return json.loads(raw)
        except Exception:
            pass
        return {}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, x-gemini-api-key")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Root route: Serve HTML template
        if path == "/" or path == "/index.html":
            html_path = os.path.join(TEMPLATES_DIR, "index.html")
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read()

                users = database.list_users()
                has_key = bool(gemini_service.get_api_key())

                options_html = ""
                for u in users:
                    options_html += f'<option value="{u["id"]}">{u["name"]} ({u["goal"]} - {u["intensity"]})</option>\n'

                content = re.sub(r'\{%\s*for u in users\s*%\}.*?\{%\s*endfor\s*%\}', options_html, content, flags=re.DOTALL)
                if has_key:
                    content = re.sub(r'\{%\s*if has_api_key\s*%\}(.*?)\{%\s*else\s*%\}.*?\{%\s*endif\s*%\}', r'\1', content, flags=re.DOTALL)
                else:
                    content = re.sub(r'\{%\s*if has_api_key\s*%\}.*?\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}', r'\1', content, flags=re.DOTALL)

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return
            else:
                self.send_error(404, "Template index.html not found")
                return

        # 2. Admin route: Serve Admin Dashboard template
        if path == "/admin" or path == "/admin.html":
            html_path = os.path.join(TEMPLATES_DIR, "admin.html")
            if os.path.exists(html_path):
                with open(html_path, "r", encoding="utf-8") as f:
                    content = f.read()

                users = database.list_users()
                stats = database.get_admin_statistics()

                # Basic template value replacements for standalone mode
                content = content.replace("{{ stats.total_users }}", str(stats.get("total_users", 0)))
                content = content.replace("{{ stats.total_plans }}", str(stats.get("total_plans", 0)))
                content = content.replace("{{ stats.total_feedbacks }}", str(stats.get("total_feedbacks", 0)))
                content = content.replace("{{ stats.total_tips }}", str(stats.get("total_tips", 0)))
                content = content.replace("{{ users|length }}", str(len(users)))

                # User table rows
                user_rows = ""
                for u in users:
                    user_rows += f"""
                    <tr class="hover:bg-slate-800/40 transition">
                        <td class="px-4 py-3.5"><div class="font-bold text-white">{u["name"]}</div></td>
                        <td class="px-4 py-3.5 text-xs text-slate-300">{u["age"]} yrs • {u["weight"]} {u.get("weight_unit", "kg")}</td>
                        <td class="px-4 py-3.5"><span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">{u["goal"]}</span></td>
                        <td class="px-4 py-3.5"><span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-300 border border-amber-500/20">{u["intensity"]}</span></td>
                        <td class="px-4 py-3.5 text-xs text-slate-300">{u.get("equipment", "all")}</td>
                        <td class="px-4 py-3.5 text-xs text-slate-500">Active</td>
                        <td class="px-4 py-3.5 text-right space-x-2">
                            <button onclick="viewUserPlan({u['id']})" class="px-2.5 py-1 text-xs font-semibold bg-slate-800 text-cyan-400 rounded-lg">View Plans</button>
                            <button onclick="deleteUserProfile({u['id']}, '{u['name']}')" class="px-2.5 py-1 text-xs font-semibold bg-rose-950/40 text-rose-300 rounded-lg">Delete</button>
                        </td>
                    </tr>
                    """
                content = re.sub(r'\{%\s*for u in users\s*%\}.*?\{%\s*endfor\s*%\}', user_rows, content, flags=re.DOTALL)
                content = re.sub(r'\{%\s*if users\s*%\}(.*?)\{%\s*else\s*%\}.*?\{%\s*endif\s*%\}', r'\1', content, flags=re.DOTALL)

                # Recent plans
                plan_rows = ""
                for p in stats.get("recent_plans", []):
                    plan_rows += f"""
                    <div class="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700 flex items-center justify-between">
                        <div>
                            <div class="flex items-center gap-2">
                                <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 font-mono">v{p.get('version', 1)}</span>
                                <h4 class="text-xs font-bold text-white">{p.get('title', 'Workout Split')}</h4>
                            </div>
                            <p class="text-[11px] text-slate-400 mt-1">Client: {p.get('user_name', 'User')} • Goal: {p.get('goal', '')}</p>
                        </div>
                        <button onclick="inspectPlanDetails({p['id']})" class="text-xs font-semibold text-emerald-400 bg-slate-800 px-2.5 py-1 rounded-lg border border-slate-700">Details</button>
                    </div>
                    """
                content = re.sub(r'\{%\s*for p in stats\.recent_plans\s*%\}.*?\{%\s*else\s*%\}.*?\{%\s*endfor\s*%\}', plan_rows or "<p class='text-xs text-slate-500'>No plans yet.</p>", content, flags=re.DOTALL)

                # Recent feedback
                fb_rows = ""
                for f in stats.get("recent_feedback", []):
                    fb_rows += f"""
                    <div class="p-3.5 rounded-xl bg-slate-800/60 border border-slate-700">
                        <span class="text-xs text-amber-400 font-semibold">{f.get('plan_title', 'Workout Split')}:</span>
                        <p class="text-xs text-slate-200 italic mt-1">"{f.get('feedback_text', '')}"</p>
                    </div>
                    """
                content = re.sub(r'\{%\s*for f in stats\.recent_feedback\s*%\}.*?\{%\s*else\s*%\}.*?\{%\s*endfor\s*%\}', fb_rows or "<p class='text-xs text-slate-500'>No feedback yet.</p>", content, flags=re.DOTALL)

                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(content.encode("utf-8"))
                return

        # 3. Static files
        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = os.path.join(STATIC_DIR, rel_path.replace("/", os.sep))
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.send_response(200)
                self.send_header("Content-Type", mime or "application/octet-stream")
                self.end_headers()
                with open(file_path, "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                self.send_error(404, "Static file not found")
                return

        # 4. API Health
        if path == "/api/health":
            self._send_json({
                "status": "healthy",
                "gemini_api_configured": bool(gemini_service.get_api_key()),
                "models": {
                    "workout_model": gemini_service.MODEL_WORKOUT_GEN,
                    "nutrition_model": gemini_service.MODEL_NUTRITION_GEN
                },
                "database": "SQLite (connected)"
            })
            return

        # 5. API Admin Stats
        if path == "/api/admin/stats":
            self._send_json(database.get_admin_statistics())
            return

        # 6. API Users
        if path == "/api/users":
            self._send_json({"users": database.list_users()})
            return

        # 7. API User Details / History: /api/plans/user/{id}
        user_plan_match = re.match(r"^/api/plans/user/(\d+)$", path)
        if user_plan_match:
            user_id = int(user_plan_match.group(1))
            user = database.get_user(user_id)
            if not user:
                self._send_json({"detail": "User not found"}, status=404)
                return
            latest = database.get_user_latest_plan(user_id)
            history = database.get_user_plan_history(user_id)
            self._send_json({
                "user": user,
                "latest_plan": latest,
                "version_history": history
            })
            return

        # 8. API Plan by ID: /api/plans/{id}
        plan_match = re.match(r"^/api/plans/(\d+)$", path)
        if plan_match:
            plan_id = int(plan_match.group(1))
            plan = database.get_workout_plan(plan_id)
            if not plan:
                self._send_json({"detail": "Plan not found"}, status=404)
                return
            self._send_json(plan)
            return

        # 9. API Tips: /api/tips
        if path == "/api/tips":
            query_params = parse_qs(parsed.query)
            goal = query_params.get("goal", [None])[0]
            tips = database.get_recent_tips(limit=10, goal=goal)
            self._send_json({"tips": tips})
            return

        # 10. API Progress Logs: /api/progress/{user_id}
        progress_match = re.match(r"^/api/progress/(\d+)$", path)
        if progress_match:
            user_id = int(progress_match.group(1))
            logs = database.get_user_progress_logs(user_id=user_id)
            self._send_json({"user_id": user_id, "logs": logs})
            return

        # 11. API Meal Plans: /api/meal-plans
        if path == "/api/meal-plans":
            plans = database.get_user_meal_plans()
            self._send_json({"meal_plans": plans})
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json_body()
        client_api_key = self.headers.get("x-gemini-api-key") or None

        # Scenario 1: Generate Plan
        if path == "/api/generate-plan":
            name = body.get("name", "User")
            age = int(body.get("age", 25))
            weight = float(body.get("weight", 70.0))
            weight_unit = body.get("weight_unit", "kg")
            goal = body.get("goal", "general wellness")
            intensity = body.get("intensity", "medium")
            equipment = body.get("equipment", "all")
            notes = body.get("notes", "")

            user_id = database.save_user(name, age, weight, goal, intensity, equipment, weight_unit, notes)

            plan_content = gemini_service.generate_workout_plan(
                name=name, age=age, weight=weight, weight_unit=weight_unit,
                goal=goal, intensity=intensity, equipment=equipment, notes=notes,
                api_key=client_api_key
            )

            plan_id = database.save_workout_plan(
                user_id=user_id,
                title=plan_content.get("title", f"7-Day {goal.title()} Protocol"),
                summary=plan_content.get("summary", ""),
                goal=goal,
                intensity=intensity,
                plan_data=plan_content,
                version=1,
                model_used=plan_content.get("model_used", gemini_service.MODEL_WORKOUT_GEN)
            )

            initial_tip = gemini_service.generate_nutrition_tip(
                goal=goal, category="nutrition",
                user_info={"name": name, "age": age, "weight": weight, "goal": goal},
                api_key=client_api_key
            )
            tip_id = database.save_nutrition_tip(
                goal=goal,
                tip_title=initial_tip.get("tip_title", "Nutritional Target"),
                tip_content=initial_tip.get("tip_content", ""),
                action_step=initial_tip.get("action_step", ""),
                category="nutrition",
                user_id=user_id,
                model_used=initial_tip.get("model_used", gemini_service.MODEL_NUTRITION_GEN)
            )

            self._send_json({
                "status": "success",
                "message": "7-day workout plan successfully created",
                "user_id": user_id,
                "plan_id": plan_id,
                "version": 1,
                "model_used": plan_content.get("model_used", gemini_service.MODEL_WORKOUT_GEN),
                "plan": plan_content,
                "nutrition_tip": {"id": tip_id, **initial_tip}
            })
            return

        # Scenario 2: Regenerate Plan with Feedback
        if path == "/api/regenerate-plan":
            plan_id = int(body.get("plan_id", 1))
            feedback_text = body.get("feedback_text", "")

            current_plan = database.get_workout_plan(plan_id)
            if not current_plan:
                self._send_json({"detail": "Plan not found"}, status=404)
                return

            user = database.get_user(current_plan["user_id"])
            if not user:
                self._send_json({"detail": "User not found"}, status=404)
                return

            database.save_plan_feedback(plan_id=plan_id, feedback_text=feedback_text)

            updated_plan_content = gemini_service.regenerate_workout_plan_with_feedback(
                current_plan=current_plan,
                feedback_text=feedback_text,
                user_info=user,
                api_key=client_api_key
            )

            new_version = current_plan["version"] + 1
            new_plan_id = database.save_workout_plan(
                user_id=user["id"],
                title=updated_plan_content.get("title", f"Refined Plan v{new_version}"),
                summary=updated_plan_content.get("summary", ""),
                goal=user["goal"],
                intensity=user["intensity"],
                plan_data=updated_plan_content,
                version=new_version,
                model_used=updated_plan_content.get("model_used", gemini_service.MODEL_WORKOUT_GEN)
            )

            feedback_history = database.get_plan_feedback_history(plan_id)

            self._send_json({
                "status": "success",
                "message": f"Plan refined successfully to version {new_version}",
                "previous_plan_id": plan_id,
                "new_plan_id": new_plan_id,
                "version": new_version,
                "user_id": user["id"],
                "model_used": updated_plan_content.get("model_used", gemini_service.MODEL_WORKOUT_GEN),
                "plan": updated_plan_content,
                "feedback_applied": feedback_text,
                "feedback_history": feedback_history
            })
            return

        # Scenario 3: Request Nutrition or Recovery Tip
        if path == "/api/nutrition-tip":
            goal = body.get("goal", "general wellness")
            category = body.get("category", "nutrition")
            user_id = body.get("user_id")

            user_info = database.get_user(user_id) if user_id else None
            tip_data = gemini_service.generate_nutrition_tip(
                goal=goal,
                category=category,
                user_info=user_info,
                api_key=client_api_key
            )

            tip_id = database.save_nutrition_tip(
                goal=goal,
                tip_title=tip_data.get("tip_title", "Nutritional Target"),
                tip_content=tip_data.get("tip_content", ""),
                action_step=tip_data.get("action_step", ""),
                category=category,
                user_id=user_id,
                model_used=tip_data.get("model_used", gemini_service.MODEL_NUTRITION_GEN)
            )

            self._send_json({
                "status": "success",
                "id": tip_id,
                "goal": goal,
                "category": category,
                "tip_title": tip_data.get("tip_title"),
                "tip_content": tip_data.get("tip_content"),
                "action_step": tip_data.get("action_step"),
                "model_used": tip_data.get("model_used", gemini_service.MODEL_NUTRITION_GEN),
                "generated_by": tip_data.get("generated_by", "Gemini Flash")
            })
            return

        # Meal Plan Endpoint
        if path == "/api/meal-plan":
            goal = body.get("goal", "general wellness")
            diet_pref = body.get("diet_preference", "omnivore")
            cals = int(body.get("calories_target", 2200))
            lang = body.get("language", "en")
            user_id = body.get("user_id")

            plan_data = gemini_service.generate_meal_plan(
                goal=goal, diet_preference=diet_pref, calories_target=cals,
                language=lang, api_key=client_api_key
            )
            plan_id = database.save_meal_plan(
                goal=goal, diet_preference=diet_pref, calories_target=cals,
                plan_data=plan_data, user_id=user_id, language=lang
            )
            self._send_json({
                "status": "success",
                "meal_plan_id": plan_id,
                "goal": goal,
                "diet_preference": diet_pref,
                "language": lang,
                "meal_plan": plan_data
            })
            return

        # AI Coach / Voice Assistant Endpoint
        if path == "/api/coach/ask":
            query = body.get("query", "")
            context = body.get("context", "")
            lang = body.get("language", "en")
            resp = gemini_service.ask_fitness_coach(query=query, context=context, language=lang, api_key=client_api_key)
            self._send_json(resp)
            return

        # Progress Log Endpoint
        if path == "/api/progress/log":
            uid = int(body.get("user_id", 1))
            ldate = body.get("log_date", "2026-10-03")
            w = float(body.get("weight", 72.0))
            wc = int(body.get("workouts_completed", 1))
            cb = int(body.get("calories_burned", 450))
            st = int(body.get("steps", 8000))
            hr = int(body.get("avg_heart_rate", 135))
            notes = body.get("notes", "")

            lid = database.save_progress_log(uid, ldate, w, wc, cb, st, hr, notes)
            self._send_json({"status": "success", "log_id": lid, "message": "Biometrics recorded"})
            return

        self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Delete user: /api/users/{id}
        match = re.match(r"^/api/users/(\d+)$", path)
        if match:
            user_id = int(match.group(1))
            success = database.delete_user(user_id)
            if success:
                self._send_json({"status": "success", "message": f"User {user_id} deleted"})
            else:
                self._send_json({"detail": "User not found"}, status=404)
            return

        self.send_error(404, "Not Found")

def run(port=PORT):
    database.init_db()
    server_address = ("", port)
    httpd = HTTPServer(server_address, FitBuddyHandler)
    print(f"\n=======================================================")
    print(f"🚀 FitBuddy Server running at: http://127.0.0.1:{port}")
    print(f"⚡ Admin Portal at: http://127.0.0.1:{port}/admin")
    print(f"🧠 Workout Engine: {gemini_service.MODEL_WORKOUT_GEN}")
    print(f"🥗 Nutrition Engine: {gemini_service.MODEL_NUTRITION_GEN}")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping FitBuddy Server...")
        httpd.server_close()

if __name__ == "__main__":
    run()
