import os
import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Database path configuration
DATABASE_FILE = os.environ.get("FITBUDDY_DB", "fitbuddy.db")
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///./{DATABASE_FILE}")

# Check if SQLAlchemy is available
try:
    from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
    from sqlalchemy.orm import declarative_base, sessionmaker, relationship
    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False

if HAS_SQLALCHEMY:
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        name = Column(String(100), nullable=False)
        age = Column(Integer, nullable=False)
        weight = Column(Float, nullable=False)
        weight_unit = Column(String(10), default="kg")
        goal = Column(String(100), nullable=False)
        intensity = Column(String(50), nullable=False)
        equipment = Column(String(100), default="full gym")
        notes = Column(Text, default="")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
        updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

        plans = relationship("WorkoutPlan", back_populates="user", cascade="all, delete-orphan")
        nutrition_tips = relationship("NutritionTip", back_populates="user")

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "age": self.age,
                "weight": self.weight,
                "weight_unit": self.weight_unit,
                "goal": self.goal,
                "intensity": self.intensity,
                "equipment": self.equipment,
                "notes": self.notes or "",
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            }

    class WorkoutPlan(Base):
        __tablename__ = "workout_plans"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        version = Column(Integer, default=1)
        title = Column(String(200), nullable=False)
        summary = Column(Text)
        goal = Column(String(100), nullable=False)
        intensity = Column(String(50), nullable=False)
        plan_data = Column(Text, nullable=False) # JSON encoded
        model_used = Column(String(50), default="gemini-1.5-pro")
        is_active = Column(Boolean, default=True)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        user = relationship("User", back_populates="plans")
        feedbacks = relationship("PlanFeedback", back_populates="plan", cascade="all, delete-orphan")

        def to_dict(self):
            try:
                parsed_data = json.loads(self.plan_data)
            except Exception:
                parsed_data = self.plan_data
            return {
                "id": self.id,
                "user_id": self.user_id,
                "version": self.version,
                "title": self.title,
                "summary": self.summary,
                "goal": self.goal,
                "intensity": self.intensity,
                "plan_data": parsed_data,
                "model_used": self.model_used,
                "is_active": self.is_active,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    class PlanFeedback(Base):
        __tablename__ = "plan_feedback"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        plan_id = Column(Integer, ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False)
        feedback_text = Column(Text, nullable=False)
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        plan = relationship("WorkoutPlan", back_populates="feedbacks")

        def to_dict(self):
            return {
                "id": self.id,
                "plan_id": self.plan_id,
                "feedback_text": self.feedback_text,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    class NutritionTip(Base):
        __tablename__ = "nutrition_tips"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
        goal = Column(String(100), nullable=False)
        category = Column(String(50), default="nutrition")
        tip_title = Column(String(200), nullable=False)
        tip_content = Column(Text, nullable=False)
        action_step = Column(Text, nullable=True)
        model_used = Column(String(50), default="gemini-1.5-flash")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        user = relationship("User", back_populates="nutrition_tips")

        def to_dict(self):
            return {
                "id": self.id,
                "user_id": self.user_id,
                "goal": self.goal,
                "category": self.category,
                "tip_title": self.tip_title,
                "tip_content": self.tip_content,
                "action_step": self.action_step,
                "model_used": self.model_used,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    class MealPlan(Base):
        __tablename__ = "meal_plans"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
        goal = Column(String(100), nullable=False)
        diet_preference = Column(String(50), default="omnivore")
        calories_target = Column(Integer, default=2200)
        plan_data = Column(Text, nullable=False) # JSON
        language = Column(String(10), default="en")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        user = relationship("User", back_populates="meal_plans")

        def to_dict(self):
            try:
                parsed = json.loads(self.plan_data)
            except Exception:
                parsed = self.plan_data
            return {
                "id": self.id,
                "user_id": self.user_id,
                "goal": self.goal,
                "diet_preference": self.diet_preference,
                "calories_target": self.calories_target,
                "plan_data": parsed,
                "language": self.language,
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    class ProgressLog(Base):
        __tablename__ = "progress_logs"

        id = Column(Integer, primary_key=True, index=True, autoincrement=True)
        user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
        log_date = Column(String(20), nullable=False)
        weight = Column(Float, nullable=False)
        workouts_completed = Column(Integer, default=1)
        calories_burned = Column(Integer, default=450)
        steps = Column(Integer, default=8000)
        avg_heart_rate = Column(Integer, default=135)
        notes = Column(Text, default="")
        created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        user = relationship("User", back_populates="progress_logs")

        def to_dict(self):
            return {
                "id": self.id,
                "user_id": self.user_id,
                "log_date": self.log_date,
                "weight": self.weight,
                "workouts_completed": self.workouts_completed,
                "calories_burned": self.calories_burned,
                "steps": self.steps,
                "avg_heart_rate": self.avg_heart_rate,
                "notes": self.notes or "",
                "created_at": self.created_at.isoformat() if self.created_at else None,
            }

    User.meal_plans = relationship("MealPlan", back_populates="user", cascade="all, delete-orphan")
    User.progress_logs = relationship("ProgressLog", back_populates="user", cascade="all, delete-orphan")

    # SQLAlchemy Engine & Session
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

else:
    engine = None
    SessionLocal = None

# ==============================================================================
# Database Initialization
# ==============================================================================
def init_db():
    """Initializes tables using SQLAlchemy ORM if present, else standard sqlite3."""
    if HAS_SQLALCHEMY and engine is not None:
        Base.metadata.create_all(bind=engine)
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            weight REAL NOT NULL,
            weight_unit TEXT DEFAULT 'kg',
            goal TEXT NOT NULL,
            intensity TEXT NOT NULL,
            equipment TEXT DEFAULT 'all',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            version INTEGER DEFAULT 1,
            title TEXT NOT NULL,
            summary TEXT,
            goal TEXT NOT NULL,
            intensity TEXT NOT NULL,
            plan_data TEXT NOT NULL,
            model_used TEXT DEFAULT 'gemini-1.5-pro',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id INTEGER NOT NULL,
            feedback_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plan_id) REFERENCES workout_plans (id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS nutrition_tips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal TEXT NOT NULL,
            category TEXT DEFAULT 'nutrition',
            tip_title TEXT NOT NULL,
            tip_content TEXT NOT NULL,
            action_step TEXT,
            model_used TEXT DEFAULT 'gemini-1.5-flash',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE SET NULL
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS meal_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            goal TEXT NOT NULL,
            diet_preference TEXT DEFAULT 'omnivore',
            calories_target INTEGER DEFAULT 2200,
            plan_data TEXT NOT NULL,
            language TEXT DEFAULT 'en',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            log_date TEXT NOT NULL,
            weight REAL NOT NULL,
            workouts_completed INTEGER DEFAULT 1,
            calories_burned INTEGER DEFAULT 450,
            steps INTEGER DEFAULT 8000,
            avg_heart_rate INTEGER DEFAULT 135,
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        );
        """)
        conn.commit()
        conn.close()

def get_db():
    """FastAPI Dependency for database session."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    else:
        yield None

# Helper connection for raw sqlite operations
def get_raw_connection():
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# ==============================================================================
# CRUD Operations (ORM + Unified Interface)
# ==============================================================================

def save_user(name: str, age: int, weight: float, goal: str, intensity: str, equipment: str = "full gym", weight_unit: str = "kg", notes: str = "") -> int:
    """Inserts a new user profile and returns user_id."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            user = User(
                name=name, age=age, weight=weight, weight_unit=weight_unit,
                goal=goal, intensity=intensity, equipment=equipment, notes=notes
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user.id
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO users (name, age, weight, weight_unit, goal, intensity, equipment, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (name, age, weight, weight_unit, goal, intensity, equipment, notes, datetime.now(timezone.utc).isoformat()))
        user_id = c.lastrowid
        conn.commit()
        conn.close()
        return user_id

def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves user profile by ID."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            return user.to_dict() if user else None
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

def list_users() -> List[Dict[str, Any]]:
    """Lists all user profiles ordered by creation descending."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            users = db.query(User).order_by(User.id.desc()).all()
            return [u.to_dict() for u in users]
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM users ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

def delete_user(user_id: int) -> bool:
    """Deletes a user and cascades deletion to their plans and feedback."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                db.delete(user)
                db.commit()
                return True
            return False
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        c.execute("DELETE FROM workout_plans WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return True

def save_workout_plan(user_id: int, title: str, summary: str, goal: str, intensity: str, plan_data: Dict[str, Any], version: int = 1, model_used: str = "gemini-1.5-pro") -> int:
    """Saves a workout plan in SQLite, deactivating any previous active plans."""
    plan_json = json.dumps(plan_data)
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            # Set prior plans for user inactive
            db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).update({"is_active": False})
            plan = WorkoutPlan(
                user_id=user_id, version=version, title=title, summary=summary,
                goal=goal, intensity=intensity, plan_data=plan_json,
                model_used=model_used, is_active=True
            )
            db.add(plan)
            db.commit()
            db.refresh(plan)
            return plan.id
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("UPDATE workout_plans SET is_active = 0 WHERE user_id = ?", (user_id,))
        c.execute("""
            INSERT INTO workout_plans (user_id, version, title, summary, goal, intensity, plan_data, model_used, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (user_id, version, title, summary, goal, intensity, plan_json, model_used))
        plan_id = c.lastrowid
        conn.commit()
        conn.close()
        return plan_id

def get_workout_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves workout plan by ID with parsed JSON data."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            plan = db.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
            return plan.to_dict() if plan else None
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM workout_plans WHERE id = ?", (plan_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        try:
            res["plan_data"] = json.loads(res["plan_data"])
        except Exception:
            pass
        return res

def get_user_latest_plan(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the active / most recent plan for a user."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            plan = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).order_by(WorkoutPlan.version.desc(), WorkoutPlan.id.desc()).first()
            return plan.to_dict() if plan else None
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM workout_plans WHERE user_id = ? ORDER BY version DESC, id DESC LIMIT 1", (user_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        res = dict(row)
        try:
            res["plan_data"] = json.loads(res["plan_data"])
        except Exception:
            pass
        return res

def get_user_plan_history(user_id: int) -> List[Dict[str, Any]]:
    """Retrieves all version iterations of a user's plans."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            plans = db.query(WorkoutPlan).filter(WorkoutPlan.user_id == user_id).order_by(WorkoutPlan.version.desc()).all()
            return [p.to_dict() for p in plans]
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT id, user_id, version, title, summary, goal, intensity, model_used, is_active, created_at FROM workout_plans WHERE user_id = ? ORDER BY version DESC", (user_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

def save_plan_feedback(plan_id: int, feedback_text: str) -> int:
    """Logs user feedback for a plan revision."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            fb = PlanFeedback(plan_id=plan_id, feedback_text=feedback_text)
            db.add(fb)
            db.commit()
            db.refresh(fb)
            return fb.id
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("INSERT INTO plan_feedback (plan_id, feedback_text) VALUES (?, ?)", (plan_id, feedback_text))
        fid = c.lastrowid
        conn.commit()
        conn.close()
        return fid

def get_plan_feedback_history(plan_id: int) -> List[Dict[str, Any]]:
    """Retrieves feedback entries associated with a plan."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            items = db.query(PlanFeedback).filter(PlanFeedback.plan_id == plan_id).order_by(PlanFeedback.created_at.asc()).all()
            return [i.to_dict() for i in items]
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM plan_feedback WHERE plan_id = ? ORDER BY created_at ASC", (plan_id,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

def save_nutrition_tip(goal: str, tip_title: str, tip_content: str, action_step: str = "", category: str = "nutrition", user_id: Optional[int] = None, model_used: str = "gemini-1.5-flash") -> int:
    """Saves a nutrition or recovery tip in SQLite."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            tip = NutritionTip(
                user_id=user_id, goal=goal, category=category,
                tip_title=tip_title, tip_content=tip_content, action_step=action_step,
                model_used=model_used
            )
            db.add(tip)
            db.commit()
            db.refresh(tip)
            return tip.id
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO nutrition_tips (user_id, goal, category, tip_title, tip_content, action_step, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, goal, category, tip_title, tip_content, action_step, model_used))
        tid = c.lastrowid
        conn.commit()
        conn.close()
        return tid

def get_recent_tips(limit: int = 10, goal: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves recently saved tips."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            query = db.query(NutritionTip)
            if goal:
                query = query.filter(NutritionTip.goal.ilike(f"%{goal}%"))
            tips = query.order_by(NutritionTip.id.desc()).limit(limit).all()
            return [t.to_dict() for t in tips]
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        if goal:
            c.execute("SELECT * FROM nutrition_tips WHERE LOWER(goal) = LOWER(?) ORDER BY id DESC LIMIT ?", (goal, limit))
        else:
            c.execute("SELECT * FROM nutrition_tips ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

def get_admin_statistics() -> Dict[str, Any]:
    """Computes administrative metrics for the admin dashboard."""
    conn = get_raw_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM workout_plans")
    total_plans = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM plan_feedback")
    total_feedbacks = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM nutrition_tips")
    total_tips = c.fetchone()[0]

    # Recent activity
    c.execute("""
        SELECT wp.id, wp.title, wp.version, wp.goal, wp.intensity, wp.created_at, u.name as user_name
        FROM workout_plans wp
        LEFT JOIN users u ON wp.user_id = u.id
        ORDER BY wp.id DESC LIMIT 8
    """)
    recent_plans = [dict(r) for r in c.fetchall()]

    c.execute("""
        SELECT pf.id, pf.feedback_text, pf.created_at, wp.title as plan_title
        FROM plan_feedback pf
        LEFT JOIN workout_plans wp ON pf.plan_id = wp.id
        ORDER BY pf.id DESC LIMIT 8
    """)
    recent_feedback = [dict(r) for r in c.fetchall()]

    conn.close()

    return {
        "total_users": total_users,
        "total_plans": total_plans,
        "total_feedbacks": total_feedbacks,
        "total_tips": total_tips,
        "recent_plans": recent_plans,
        "recent_feedback": recent_feedback,
    }

def save_meal_plan(goal: str, diet_preference: str, calories_target: int, plan_data: Dict[str, Any], user_id: Optional[int] = None, language: str = "en") -> int:
    """Saves daily meal plan in SQLite."""
    plan_json = json.dumps(plan_data)
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            mp = MealPlan(
                user_id=user_id, goal=goal, diet_preference=diet_preference,
                calories_target=calories_target, plan_data=plan_json, language=language
            )
            db.add(mp)
            db.commit()
            db.refresh(mp)
            return mp.id
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO meal_plans (user_id, goal, diet_preference, calories_target, plan_data, language)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, goal, diet_preference, calories_target, plan_json, language))
        mid = c.lastrowid
        conn.commit()
        conn.close()
        return mid

def get_user_meal_plans(user_id: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieves meal plans."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            query = db.query(MealPlan)
            if user_id:
                query = query.filter(MealPlan.user_id == user_id)
            plans = query.order_by(MealPlan.id.desc()).limit(limit).all()
            return [p.to_dict() for p in plans]
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        if user_id:
            c.execute("SELECT * FROM meal_plans WHERE user_id = ? ORDER BY id DESC LIMIT ?", (user_id, limit))
        else:
            c.execute("SELECT * FROM meal_plans ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
        res = []
        for r in rows:
            d = dict(r)
            try:
                d["plan_data"] = json.loads(d["plan_data"])
            except Exception:
                pass
            res.append(d)
        return res

def save_progress_log(user_id: int, log_date: str, weight: float, workouts_completed: int = 1, calories_burned: int = 450, steps: int = 8000, avg_heart_rate: int = 135, notes: str = "") -> int:
    """Saves daily workout and biometric tracking log."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            log = ProgressLog(
                user_id=user_id, log_date=log_date, weight=weight,
                workouts_completed=workouts_completed, calories_burned=calories_burned,
                steps=steps, avg_heart_rate=avg_heart_rate, notes=notes
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            return log.id
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("""
            INSERT INTO progress_logs (user_id, log_date, weight, workouts_completed, calories_burned, steps, avg_heart_rate, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, log_date, weight, workouts_completed, calories_burned, steps, avg_heart_rate, notes))
        lid = c.lastrowid
        conn.commit()
        conn.close()
        return lid

def get_user_progress_logs(user_id: int, limit: int = 14) -> List[Dict[str, Any]]:
    """Retrieves progress logs for a user ordered by date ascending for charts."""
    if HAS_SQLALCHEMY and SessionLocal is not None:
        db = SessionLocal()
        try:
            logs = db.query(ProgressLog).filter(ProgressLog.user_id == user_id).order_by(ProgressLog.id.asc()).limit(limit).all()
            return [l.to_dict() for l in logs]
        finally:
            db.close()
    else:
        conn = get_raw_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM progress_logs WHERE user_id = ? ORDER BY id ASC LIMIT ?", (user_id, limit))
        rows = c.fetchall()
        conn.close()
        return [dict(r) for r in rows]

