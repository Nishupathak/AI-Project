import collections
import datetime
import difflib
import json
import os
import queue
import random
import re
import sqlite3
import subprocess
import threading
import time
import traceback
import urllib.error
import urllib.request
import base64
import webbrowser
from urllib.parse import quote_plus

import cv2
import mediapipe as mp
import numpy as np
import sounddevice as sd
import speech_recognition as sr
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision
from pydantic import BaseModel

folder = os.path.dirname(os.path.abspath(__file__))
NO_WINDOW = 0x08000000  # hide PowerShell windows

state = {"faces": 0, "fingers": 0, "expression": "-", "jpeg": None, "mic": True,
         "speaking": False, "last_spoke": 0.0, "mic_error": "",
         "labels": [], "embeddings": [], "enroll": None, "id_error": ""}
state.update({"fps": 0.0, "mic_level": 0.0, "mic_threshold": 0.0, "voice_state": "listening",
              "signals": {}, "voice_on": True, "started": time.time(), "age_ready": False})
latencies = collections.deque(maxlen=40)  # how long each command took to answer
history = []  # last messages kept in memory for the dashboard


# ======================= DATABASE (SQLite) =======================
db = None
db_lock = threading.Lock()


def init_db(path=None):
    global db
    db = sqlite3.connect(path or os.path.join(folder, "robot.db"), check_same_thread=False)
    with db_lock:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS people(
                name TEXT PRIMARY KEY, embeddings TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS history(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, you TEXT, robot TEXT);
            CREATE TABLE IF NOT EXISTS detections(
                id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, faces INTEGER,
                fingers INTEGER, expression TEXT, person TEXT);
        """)
        db.commit()
        rows = db.execute("SELECT you, robot FROM history ORDER BY id DESC LIMIT 30").fetchall()
    history.clear()
    history.extend({"you": y, "robot": r} for y, r in reversed(rows))
    print("Database ready:", os.path.basename(path or "robot.db"))


def add_history(you, robot):
    history.append({"you": you, "robot": robot})
    if db is None:
        return
    try:
        with db_lock:
            db.execute("INSERT INTO history(ts, you, robot) VALUES (?,?,?)",
                       (datetime.datetime.now().isoformat(timespec="seconds"), you, robot))
            db.commit()
    except Exception as e:
        print("DB error:", e)


def db_history(limit=50):
    with db_lock:
        rows = db.execute("SELECT ts, you, robot FROM history ORDER BY id DESC LIMIT ?",
                          (limit,)).fetchall()
    return [{"ts": t, "you": y, "robot": r} for t, y, r in rows]


def db_stats():
    with db_lock:
        commands = db.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        detections = db.execute("SELECT COUNT(*) FROM detections").fetchone()[0]
        top = db.execute("SELECT expression FROM detections WHERE expression != '-' "
                         "GROUP BY expression ORDER BY COUNT(*) DESC LIMIT 1").fetchone()
    return {"commands": commands, "detections": detections, "people": len(people),
            "top_expression": top[0] if top else ""}


def db_detection_summary():
    with db_lock:
        by_expr = db.execute("SELECT expression, COUNT(*) FROM detections WHERE expression != '-' "
                             "GROUP BY expression ORDER BY COUNT(*) DESC").fetchall()
        recent = db.execute("SELECT ts, faces, fingers, expression, person FROM detections "
                            "ORDER BY id DESC LIMIT 6").fetchall()
    return {"expressions": [{"name": n, "count": c} for n, c in by_expr],
            "recent": [{"ts": t, "faces": f, "fingers": fi, "expression": e, "person": p}
                       for t, f, fi, e, p in recent]}


def db_clear_history():
    history.clear()
    with db_lock:
        db.execute("DELETE FROM history")
        db.commit()


def log_worker():
    """Every 5 seconds, save what the robot currently sees."""
    while True:
        time.sleep(5)
        if db is None or not (state["faces"] > 0 or state["fingers"] > 0):
            continue
        person = state["labels"][0][0] if state["labels"] else ""
        try:
            with db_lock:
                db.execute("INSERT INTO detections(ts, faces, fingers, expression, person) "
                           "VALUES (?,?,?,?,?)",
                           (datetime.datetime.now().isoformat(timespec="seconds"),
                            state["faces"], state["fingers"], state["expression"], person))
                db.commit()
        except Exception as e:
            print("DB error:", e)


# ======================= MOUTH: Windows built-in voice =======================
speech_q = queue.Queue()


def say(text):
    env = dict(os.environ, ROBOT_TEXT=text)
    script = ("Add-Type -AssemblyName System.Speech; "
              "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
              "$s.Speak($env:ROBOT_TEXT)")
    subprocess.run(["powershell", "-NoProfile", "-Command", script],
                   env=env, creationflags=NO_WINDOW, timeout=60)


def speech_worker():
    while True:
        text = speech_q.get()
        state["speaking"] = True
        try:
            print("Robot:", text)
            say(text)
        except Exception as e:
            print("Speech error:", e)
        state["last_spoke"] = time.time()
        state["speaking"] = False


# ======================= APPS: open anything installed =======================
apps_cache = {"list": None}

WEBSITES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "github": "https://github.com",
    "maps": "https://maps.google.com",
}


def installed_apps():
    if apps_cache["list"] is None:
        try:
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json"],
                capture_output=True, text=True, timeout=40, creationflags=NO_WINDOW).stdout
            data = json.loads(out)
            if isinstance(data, dict):
                data = [data]
            apps_cache["list"] = [(a["Name"], a["AppID"]) for a in data]
            print(f"Found {len(apps_cache['list'])} installed apps")
        except Exception as e:
            print("App list error:", e)
            apps_cache["list"] = []
    return apps_cache["list"]


def open_app(name):
    name = re.sub(r"\s+(app|application|please)$", "", name.strip().lower())
    if name in WEBSITES:
        webbrowser.open(WEBSITES[name])
        return f"Opening {name}"
    apps = installed_apps()
    matches = [a for a in apps if name in a[0].lower()]
    if not matches:
        close = difflib.get_close_matches(name, [a[0].lower() for a in apps], n=1, cutoff=0.6)
        matches = [a for a in apps if close and a[0].lower() == close[0]]
    if not matches:
        return f"I could not find an app called {name}"
    app = min(matches, key=lambda a: len(a[0]))  # shortest name = best match
    subprocess.Popen(["explorer.exe", "shell:AppsFolder\\" + app[1]])
    return f"Opening {app[0]}"


# ======================= IDENTITY: name + age =======================
SFACE_FILE = "face_recognition_sface_2021dec.onnx"
AGE_FILE = "age_googlenet.onnx"
SFACE_URL = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
             "face_recognition_sface/face_recognition_sface_2021dec.onnx")
AGE_URL = ("https://github.com/onnx/models/raw/main/validated/vision/"
           "body_analysis/age_gender/models/age_googlenet.onnx")
AGE_BUCKETS = ["0-2", "4-6", "8-12", "15-20", "25-32", "38-43", "48-53", "60+"]
PEOPLE_FILE = os.path.join(folder, "people.json")
MATCH_THRESHOLD = 0.363  # cosine similarity used by SFace

TEMPLATE = np.array([[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
                     [41.5493, 92.3655], [70.7299, 92.2041]], dtype=np.float32)

ident_q = queue.Queue(maxsize=1)
people = {}  # name -> list of normalized embeddings


def load_people():
    try:
        with db_lock:
            rows = db.execute("SELECT name, embeddings FROM people").fetchall()
        for name, emb in rows:
            people[name] = [np.array(x, dtype=np.float32) for x in json.loads(emb)]
        if not rows and os.path.exists(PEOPLE_FILE):  # one-time move from the old JSON file
            data = json.load(open(PEOPLE_FILE))
            for name, samples in data.items():
                people[name] = [np.array(x, dtype=np.float32) for x in samples]
            save_people()
            os.replace(PEOPLE_FILE, PEOPLE_FILE + ".bak")
            print("Moved people.json into the database")
        print("Known people:", ", ".join(people) or "none")
    except Exception as e:
        print("Could not load people:", e)


def save_people():
    with db_lock:
        db.execute("DELETE FROM people")
        db.executemany("INSERT INTO people(name, embeddings) VALUES (?,?)",
                       [(n, json.dumps([x.tolist() for x in v])) for n, v in people.items()])
        db.commit()


def get_model(filename, url):
    path = os.path.join(folder, filename)
    if not os.path.exists(path):
        print("Downloading", filename, "(one time, may take a minute) ...")
        urllib.request.urlretrieve(url, path)
        if os.path.getsize(path) < 1_000_000:  # got a text pointer, not the real model
            os.remove(path)
            raise RuntimeError("download incomplete")
    return path


def match_person(emb):
    e = emb / (np.linalg.norm(emb) + 1e-9)
    best, best_sim = "Unknown", MATCH_THRESHOLD
    for name, samples in people.items():
        for sample in samples:
            sim = float(np.dot(e, sample))
            if sim > best_sim:
                best, best_sim = name, sim
    return best


def make_job(raw, lms, w, h, box):
    """Crop the face for recognition (aligned 112x112) and for age (224x224)."""
    job = {"aligned": None, "age": None}
    try:
        def pt(i):
            return np.array([lms[i].x * w, lms[i].y * h], dtype=np.float32)
        eyes = sorted([pt(468), pt(473)], key=lambda q: q[0])
        mouth = sorted([pt(61), pt(291)], key=lambda q: q[0])
        src = np.array([eyes[0], eyes[1], pt(1), mouth[0], mouth[1]], dtype=np.float32)
        M, _ = cv2.estimateAffinePartial2D(src, TEMPLATE, method=cv2.LMEDS)
        if M is not None:
            job["aligned"] = cv2.warpAffine(raw, M, (112, 112))
        x1, y1, x2, y2 = box
        pad = int(0.15 * max(x2 - x1, y2 - y1))
        crop = raw[max(y1 - pad, 0):min(y2 + pad, h), max(x1 - pad, 0):min(x2 + pad, w)]
        if crop.size:
            job["age"] = cv2.resize(crop, (224, 224))
    except Exception:
        pass
    return job


def ident_worker():
    sface = age_net = None
    try:
        sface = cv2.dnn.readNetFromONNX(get_model(SFACE_FILE, SFACE_URL))
        print("Face recognition ready")
    except Exception as e:
        state["id_error"] = "name recognition off"
        print("Name recognition model failed:", e)
    try:
        age_net = cv2.dnn.readNetFromONNX(get_model(AGE_FILE, AGE_URL))
        state["age_ready"] = True
        print("Age model ready")
    except Exception as e:
        print("Age model failed:", e)

    state["sface_ready"] = sface is not None
    while True:
        jobs = ident_q.get()
        try:
            labels, embs = [], []
            for job in jobs:
                name, age, emb = "", "", None
                if sface is not None and job["aligned"] is not None:
                    blob = cv2.dnn.blobFromImage(job["aligned"], 1.0, (112, 112), (0, 0, 0),
                                                 swapRB=True, crop=False)
                    sface.setInput(blob)
                    emb = sface.forward().flatten()
                    name = match_person(emb)
                if age_net is not None and job["age"] is not None:
                    blob = cv2.dnn.blobFromImage(job["age"], 1.0, (224, 224), (104, 117, 123),
                                                 swapRB=False, crop=False)
                    age_net.setInput(blob)
                    probs = age_net.forward().flatten()
                    if len(probs) == len(AGE_BUCKETS):
                        age = AGE_BUCKETS[int(np.argmax(probs))]
                labels.append((name, age))
                embs.append(emb)
            state["labels"] = labels
            state["embeddings"] = embs

            enroll = state["enroll"]
            if enroll and embs and embs[0] is not None:
                enroll["samples"].append(embs[0] / (np.linalg.norm(embs[0]) + 1e-9))
                if len(enroll["samples"]) >= 8:
                    people[enroll["name"]] = enroll["samples"]
                    save_people()
                    state["enroll"] = None
                    msg = f"Done. I will remember {enroll['name']}"
                    add_history("(system)", msg)
                    speech_q.put(msg)
        except Exception:
            traceback.print_exc()


def start_enroll(name):
    name = name.strip().title()
    if not state.get("sface_ready"):
        return "My face recognition model is not ready"
    if state["faces"] == 0:
        return "I cannot see your face"
    state["enroll"] = {"name": name, "samples": []}
    return f"Okay {name}. Look at the camera and turn your head slightly for four seconds"


# ======================= LLM BRAIN (Gemini free tier or Claude) =======================
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/"
GEMINI_URL = GEMINI_BASE + "models/{model}:generateContent"
FALLBACK_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.5-flash",
                   "gemini-3-flash-preview", "gemini-2.5-flash-lite"]  # used only if listing fails
gemini_models = {"list": None}
CLAUDE_MODEL = "claude-haiku-5-5"
CLAUDE_URL = "https://api.anthropic.com/v1/messages"


def get_llm():
    """Returns (provider, key). Key comes from api_key.txt or an environment variable."""
    key = ""
    path = os.path.join(folder, "api_key.txt")
    if os.path.exists(path):
        key = open(path, encoding="utf-8-sig").read().strip().strip("\"'").strip()
    key = key or os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        return "", ""
    return ("Claude" if key.startswith("sk-ant") else "Gemini"), key


def build_context(with_image):
    who = state["labels"][0][0] if state["labels"] else ""
    system = (
        "You are a friendly desk robot talking out loud to your owner. "
        "Reply in one to three short, plain sentences. No markdown, no lists, no emojis. "
        "If you do not know something, say so briefly. "
        f"Live camera info: {state['faces']} face(s), {state['fingers']} finger(s) raised, "
        f"expression {state['expression']}, person {who or 'unknown'}. "
        f"Current time: {datetime.datetime.now().strftime('%A %d %B %Y, %I:%M %p')}."
    )
    turns = []  # short memory of the recent conversation
    for h in history[-6:]:
        if h["you"] and not h["you"].startswith("("):
            turns.append(("user", h["you"]))
            turns.append(("assistant", h["robot"]))
    image = state["jpeg"] if (with_image and state["jpeg"]) else None
    return system, turns, image


def http_json(url, body, headers, method="POST"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        e.detail = e.read().decode(errors="ignore")[:400]
        raise


def discover_gemini_models(key):
    """Ask Google which fast 'flash' models this key can use (names change over time)."""
    data = http_json(GEMINI_BASE + "models?pageSize=200", None, {"x-goog-api-key": key}, method="GET")
    skip = ("image", "tts", "live", "audio", "native", "embedding", "robotics", "computer", "learnlm", "gemma")
    found = []
    for m in data.get("models", []):
        name = m.get("name", "").replace("models/", "")
        if "generateContent" not in m.get("supportedGenerationMethods", []):
            continue
        if "flash" not in name or any(x in name for x in skip):
            continue
        found.append(name)

    def rank(n):  # stable first, then lite (cheapest), then newest
        v = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return (("preview" in n or "exp" in n), ("lite" not in n), -(float(v.group(1)) if v else 0))
    return sorted(found, key=rank)[:4]


def call_gemini(key, question, system, turns, image):
    contents = [{"role": "user" if r == "user" else "model", "parts": [{"text": t}]} for r, t in turns]
    parts = []
    if image:
        parts.append({"inlineData": {"mimeType": "image/jpeg",
                                     "data": base64.b64encode(image).decode()}})
    parts.append({"text": question})
    contents.append({"role": "user", "parts": parts})

    models = gemini_models["list"]
    if models is None:
        try:
            models = discover_gemini_models(key)
        except Exception as e:
            print("Could not list Gemini models:", getattr(e, "detail", e))
            models = []
        models = models or FALLBACK_MODELS
        gemini_models["list"] = models
        print("Gemini models to try:", models)

    headers = {"x-goog-api-key": key, "content-type": "application/json"}
    last_error = None
    for model in models:
        for thinking_off in (True, False):  # some models reject the thinking setting
            config = {"maxOutputTokens": 1024}
            if thinking_off:
                config["thinkingConfig"] = {"thinkingBudget": 0}
            body = {"systemInstruction": {"parts": [{"text": system}]},
                    "contents": contents, "generationConfig": config}
            try:
                data = http_json(GEMINI_URL.format(model=model), body, headers)
                cands = data.get("candidates") or []
                texts = [p.get("text", "") for c in cands[:1]
                         for p in c.get("content", {}).get("parts", [])]
                return "".join(texts).strip() or "I cannot answer that one"
            except urllib.error.HTTPError as e:
                last_error = e
                print(f"Gemini {model} -> HTTP {e.code}: {getattr(e, 'detail', '')[:200]}")
                if e.code in (401, 403, 429) or "api key" in getattr(e, "detail", "").lower():
                    raise  # key or quota problem: another model will not help
                if e.code == 400 and thinking_off and "think" in getattr(e, "detail", "").lower():
                    continue  # retry the same model without the thinking setting
                if e.code in (404, 400):
                    break  # model not usable, try the next one
                raise
    gemini_models["list"] = None  # re-discover next time
    raise last_error


def call_claude(key, question, system, turns, image):
    messages = [{"role": r, "content": t} for r, t in turns]
    content = []
    if image:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                    "data": base64.b64encode(image).decode()}})
    content.append({"type": "text", "text": question})
    messages.append({"role": "user", "content": content})
    data = http_json(CLAUDE_URL,
                     {"model": CLAUDE_MODEL, "max_tokens": 250, "system": system, "messages": messages},
                     {"x-api-key": key, "anthropic-version": "2023-06-01",
                      "content-type": "application/json"})
    return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()


def llm_diagnose():
    """Used by /llm/test so you can see exactly what is wrong."""
    provider, key = get_llm()
    if not key:
        return {"ok": False, "problem": "No key found. Check api_key.txt is in the same folder as server.py "
                                          "and is not named api_key.txt.txt"}
    out = {"provider": provider, "key_length": len(key), "key_starts_with": key[:4]}
    try:
        if provider == "Gemini":
            out["models_found"] = discover_gemini_models(key)
        system, turns, image = build_context(False)
        call = call_gemini if provider == "Gemini" else call_claude
        out["reply"] = call(key, "Say the word ok.", system, [], None)
        out["ok"] = True
    except urllib.error.HTTPError as e:
        out.update(ok=False, http_status=e.code, detail=getattr(e, "detail", ""))
    except Exception as e:
        out.update(ok=False, problem=f"{type(e).__name__}: {e}")
    return out


def ask_llm(question, with_image=False):
    provider, key = get_llm()
    if not key:
        return "I need an API key to answer that. Save it in a file called api_key.txt"
    system, turns, image = build_context(with_image)
    try:
        call = call_gemini if provider == "Gemini" else call_claude
        text = call(key, question, system, turns, image)
        text = re.sub(r"[*#`_]", "", text)  # no markdown symbols when speaking
        return text or "I have no answer for that"
    except urllib.error.HTTPError as e:
        detail = getattr(e, "detail", "") or ""
        print("LLM error", e.code, detail)
        low = detail.lower()
        if e.code in (401, 403) or "api key not valid" in low or "api_key_invalid" in low:
            return "My API key was rejected. Please check api_key.txt"
        if e.code == 429:
            return "I have used up my free questions for now. Try again in a minute"
        if "credit" in low:
            return "My API account is out of credit"
        return "I could not reach my brain right now"
    except Exception as e:
        print("LLM error:", e)
        return "I could not reach my brain right now"


# ======================= BRAIN: command handler =======================
def handle(cmd):
    cmd = cmd.lower().strip().rstrip(".?!")

    # --- teach the robot a face: "remember me as Nishu" ---
    m = re.match(r"^(?:please\s+)?(?:remember me as|remember this face as|remember my face as|"
                 r"learn my face as|my name is|call me)\s+(.+)$", cmd)
    if m:
        return start_enroll(m.group(1))

    if cmd.startswith("forget"):
        target = cmd.replace("forget", "", 1).strip()
        if target in ("everyone", "all", "everybody", ""):
            people.clear()
            save_people()
            return "I forgot everyone"
        for n in list(people):
            if n.lower() == target:
                del people[n]
                save_people()
                return f"I forgot {n}"
        return f"I do not know anyone called {target}"

    if re.search(r"\bwho am i\b|who is this|what is my name|do you know me", cmd):
        if state["faces"] == 0 or not state["labels"]:
            return "I cannot see anyone"
        who = state["labels"][0][0]
        if who in ("", "Unknown"):
            return "I do not know you yet. Say, remember me as, and then your name"
        return f"You are {who}"

    if re.search(r"how old (am i|do i look)|my age|guess my age", cmd):
        if state["faces"] == 0 or not state["labels"] or not state["labels"][0][1]:
            return "I cannot tell yet"
        return f"I think you are about {state['labels'][0][1]} years old"

    # --- web search: "search python tutorials on google" ---
    m = re.match(r"^(?:please\s+)?(search|google|look up)\b\s*(.*)$", cmd)
    if m:
        q = m.group(2)
        site = "youtube" if "youtube" in q else "google"
        q = re.sub(r"\b(on|in|at)\s+(google|youtube)\b", "", q).strip()
        q = re.sub(r"^(google|youtube)\s*", "", q).strip()
        q = re.sub(r"^(for|about)\s+", "", q).strip()
        if not q:
            return "What should I search for?"
        base = ("https://www.youtube.com/results?search_query="
                if site == "youtube" else "https://www.google.com/search?q=")
        webbrowser.open(base + quote_plus(q))
        return f"Searching {site} for {q}"

    # --- play something on youtube ---
    m = re.match(r"^(?:please\s+)?play\s+(.+)$", cmd)
    if m:
        q = re.sub(r"\s*(on|in)\s+youtube$", "", m.group(1)).strip()
        webbrowser.open("https://www.youtube.com/results?search_query=" + quote_plus(q))
        return f"Playing {q} on YouTube"

    # --- open any app or site: "open telegram" ---
    m = re.match(r"^(?:please\s+)?(?:open|launch|start|run)\s+(?:the\s+)?(.+)$", cmd)
    if m:
        return open_app(m.group(1))

    # --- ask the LLM about what the camera sees ---
    if re.search(r"what (do |can )?you see|describe (what|the|this|my)|what am i holding|"
                 r"what is this|what's this|what is in (front|my hand)|what('s| is) in my hand", cmd):
        return ask_llm(cmd, with_image=True)

    # --- expression ---
    if any(w in cmd for w in ("expression", "emotion", "mood", "how do i look",
                              "am i smiling", "am i happy", "am i sad")):
        if state["faces"] == 0:
            return "I cannot see your face"
        return f"You look {state['expression'].lower()}"

    if re.search(r"\bfingers?\b", cmd):
        n = state["fingers"]
        return f"I can see {n} finger" + ("" if n == 1 else "s")
    if re.search(r"\bfaces?\b", cmd):
        n = state["faces"]
        if n == 0:
            return "I cannot see any face"
        return f"I can see {n} face" + ("" if n == 1 else "s")
    if cmd.startswith("repeat") or cmd.startswith("say "):
        words = cmd.split(" ", 1)
        return words[1] if len(words) > 1 else "Repeat what?"
    if re.search(r"what('s| is) the time|what time|current time|tell me the time|time is it", cmd):
        return "It is " + datetime.datetime.now().strftime("%I:%M %p")
    if re.search(r"^(what('s| is) )?(today'?s date|the date( today)?)$|what day (is it|is today|today)|"
                 r"which day is (it|today)|date today|tell me the date|what('s| is) the date today", cmd):
        return "Today is " + datetime.datetime.now().strftime("%A, %d %B %Y")
    if re.search(r"\b(take|capture|click|snap)\b.*\b(photo|picture|selfie|pic)\b|\bselfie\b", cmd):
        if state["jpeg"] is None:
            return "My camera is not ready"
        os.makedirs(os.path.join(folder, "photos"), exist_ok=True)
        name = datetime.datetime.now().strftime("photo_%Y%m%d_%H%M%S.jpg")
        with open(os.path.join(folder, "photos", name), "wb") as f:
            f.write(state["jpeg"])
        return "Photo saved in the photos folder"
    if "joke" in cmd:
        return random.choice([
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "I told my computer I needed a break, and it froze.",
            "Why did the robot go on vacation? It needed to recharge.",
        ])
    if "how are you" in cmd:
        return "I am running at one hundred percent. Thanks for asking!"
    if re.search(r"what('s| is) your name|who are you", cmd):
        return "I am your AI robot"
    if re.fullmatch(r"(hello|hi|hey)( there| robot)?", cmd):
        return "Hello! I am your robot."

    # --- anything else: ask the LLM ---
    return ask_llm(cmd)


def respond(cmd):
    t0 = time.time()
    try:
        reply = handle(cmd)
    except Exception as e:
        traceback.print_exc()
        reply = "Something went wrong with that command"
    ms = int((time.time() - t0) * 1000)
    latencies.append({"t": datetime.datetime.now().strftime("%H:%M:%S"), "ms": ms, "cmd": cmd[:28]})
    add_history(cmd, reply)
    if state["voice_on"]:
        speech_q.put(reply)
    return reply


# ======================= EARS: continuous microphone =======================
def mic_worker():
    recognizer = sr.Recognizer()
    FS = 16000
    BLOCK = int(FS * 0.1)  # 100 ms blocks
    while True:
        try:
            with sd.InputStream(samplerate=FS, channels=1, dtype="int16", blocksize=BLOCK) as stream:
                noise = []
                for _ in range(10):  # measure room noise for 1 second
                    data, _ = stream.read(BLOCK)
                    noise.append(float(np.abs(data).mean()))
                threshold = max(float(np.mean(noise)) * 3, 250.0)
                state["mic_threshold"] = threshold
                print(f"Mic ready (noise threshold {threshold:.0f})")
                state["mic_error"] = ""

                preroll = collections.deque(maxlen=3)
                frames, talking, silence = [], False, 0
                while True:
                    data, _ = stream.read(BLOCK)
                    busy = (not state["mic"] or state["speaking"] or not speech_q.empty()
                            or time.time() - state["last_spoke"] < 0.7)
                    if busy:  # do not listen to our own voice
                        state["voice_state"] = "muted" if not state["mic"] else "speaking"
                        state["mic_level"] = 0.0
                        frames, talking, silence = [], False, 0
                        preroll.clear()
                        continue

                    level = float(np.abs(data).mean())
                    state["mic_level"] = level
                    state["voice_state"] = "hearing" if (talking or level > threshold) else "listening"
                    if level > threshold:
                        if not talking:
                            frames = list(preroll)
                            talking = True
                        frames.append(data)
                        silence = 0
                    elif talking:
                        frames.append(data)
                        silence += 1
                    else:
                        preroll.append(data)

                    if talking and (silence >= 8 or len(frames) > 150):
                        if len(frames) >= 6:  # ignore tiny noises
                            state["voice_state"] = "thinking"
                            audio = sr.AudioData(np.concatenate(frames).tobytes(), FS, 2)
                            try:
                                text = recognizer.recognize_google(audio)
                                print("You:", text)
                                respond(text)
                            except sr.UnknownValueError:
                                pass
                            except sr.RequestError:
                                add_history("(mic)", "Internet problem")
                        frames, talking, silence = [], False, 0
                        preroll.clear()
        except Exception as e:
            state["mic_error"] = str(e)[:80]
            print("Mic error:", e)
            time.sleep(2)


# ======================= EYES: camera, faces, expressions, fingers =======================
BASE = "https://storage.googleapis.com/mediapipe-models/"
MODELS = {
    "face_landmarker.task": BASE + "face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "hand.task": BASE + "hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
}


def get_expression(blendshapes):
    s = {c.category_name: c.score for c in blendshapes}
    smile = (s.get("mouthSmileLeft", 0) + s.get("mouthSmileRight", 0)) / 2
    jaw = s.get("jawOpen", 0)
    brow_up = s.get("browInnerUp", 0)
    eye_wide = (s.get("eyeWideLeft", 0) + s.get("eyeWideRight", 0)) / 2
    brow_down = (s.get("browDownLeft", 0) + s.get("browDownRight", 0)) / 2
    frown = (s.get("mouthFrownLeft", 0) + s.get("mouthFrownRight", 0)) / 2
    if jaw > 0.4 and (brow_up > 0.3 or eye_wide > 0.3):
        return "Surprised"
    if smile > 0.4:
        return "Happy"
    if brow_down > 0.45:
        return "Angry"
    if frown > 0.25 or brow_up > 0.5:
        return "Sad"
    return "Neutral"


def get_signals(blendshapes):
    """The raw facial-muscle scores (0..1) that the expression rules look at."""
    s = {c.category_name: c.score for c in blendshapes}
    avg = lambda a, b: round((s.get(a, 0) + s.get(b, 0)) / 2, 2)
    return {"smile": avg("mouthSmileLeft", "mouthSmileRight"),
            "jawOpen": round(s.get("jawOpen", 0), 2),
            "browRaise": round(s.get("browInnerUp", 0), 2),
            "browDown": avg("browDownLeft", "browDownRight"),
            "frown": avg("mouthFrownLeft", "mouthFrownRight"),
            "eyesWide": avg("eyeWideLeft", "eyeWideRight"),
            "blink": avg("eyeBlinkLeft", "eyeBlinkRight")}


def count_fingers(lm, label):
    fingers = 0
    if label == "Right":
        fingers += lm[4].x < lm[3].x
    else:
        fingers += lm[4].x > lm[3].x
    for tip, pip in [(8, 6), (12, 10), (16, 14), (20, 18)]:
        fingers += lm[tip].y < lm[pip].y
    return int(fingers)


def camera_worker():
    try:
        for name, url in MODELS.items():
            path = os.path.join(folder, name)
            if not os.path.exists(path):
                print("Downloading", name, "...")
                urllib.request.urlretrieve(url, path)

        face_lm = vision.FaceLandmarker.create_from_options(
            vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=os.path.join(folder, "face_landmarker.task")),
                output_face_blendshapes=True, num_faces=3))
        hand_det = vision.HandLandmarker.create_from_options(
            vision.HandLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_path=os.path.join(folder, "hand.task")),
                num_hands=2))
        cap = cv2.VideoCapture(0)
        print("Camera ready")
        last_t = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.5)
                continue
            frame = cv2.flip(frame, 1)
            raw = frame.copy()
            h, w, _ = frame.shape
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

            res = face_lm.detect(image)
            first_expr = "-"
            first_signals = {}
            jobs = []
            labels = state["labels"]
            for i, lms in enumerate(res.face_landmarks):
                xs = [l.x * w for l in lms]
                ys = [l.y * h for l in lms]
                x1, y1, x2, y2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))
                expr = get_expression(res.face_blendshapes[i]) if res.face_blendshapes else "Neutral"
                if i == 0:
                    first_expr = expr
                    if res.face_blendshapes:
                        first_signals = get_signals(res.face_blendshapes[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(frame, expr, (x1, max(y1 - 10, 25)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                if i < len(labels):
                    title = ", ".join(t for t in labels[i] if t)
                    if title:
                        cv2.putText(frame, title, (x1, max(y1 - 38, 25)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
                jobs.append(make_job(raw, lms, w, h, (x1, y1, x2, y2)))

            if jobs:
                try:
                    ident_q.put_nowait(jobs)
                except queue.Full:
                    pass
            else:
                state["labels"] = []

            total = 0
            hands = hand_det.detect(image)
            for lms, handed in zip(hands.hand_landmarks, hands.handedness):
                total += count_fingers(lms, handed[0].category_name)
                for p in lms:
                    cv2.circle(frame, (int(p.x * w), int(p.y * h)), 4, (255, 0, 0), -1)

            state["faces"] = len(res.face_landmarks)
            state["fingers"] = total
            state["expression"] = first_expr
            state["signals"] = first_signals
            ok, buf = cv2.imencode(".jpg", frame)
            if ok:
                state["jpeg"] = buf.tobytes()
            now = time.time()
            inst = 1.0 / max(now - last_t, 1e-3)
            last_t = now
            state["fps"] = inst if state["fps"] == 0 else 0.9 * state["fps"] + 0.1 * inst
    except Exception:
        print("Camera thread crashed:")
        traceback.print_exc()


# ======================= DATA FOR THE DASHBOARD =======================
def identify_details():
    """Cosine similarity between the face on camera and every saved person."""
    embs = state["embeddings"]
    if not embs or embs[0] is None:
        return {"face": False, "embedding": [], "similarities": [], "threshold": MATCH_THRESHOLD, "best": ""}
    e = embs[0] / (np.linalg.norm(embs[0]) + 1e-9)
    sims = [{"name": n, "similarity": round(max(float(np.dot(e, x)) for x in v), 3)}
            for n, v in people.items() if v]
    sims.sort(key=lambda x: -x["similarity"])
    best = sims[0]["name"] if sims and sims[0]["similarity"] >= MATCH_THRESHOLD else "Unknown"
    return {"face": True, "embedding": [round(float(x), 3) for x in e], "similarities": sims,
            "threshold": MATCH_THRESHOLD, "best": best}


def system_info():
    provider, _ = get_llm()
    return {
        "uptime_s": int(time.time() - state["started"]),
        "fps": round(state["fps"], 1),
        "voice_on": state["voice_on"], "mic": state["mic"],
        "models": [
            {"name": "Face Landmarker", "detail": "MediaPipe, 478 landmarks + 52 blendshapes", "ready": state["jpeg"] is not None},
            {"name": "Hand Landmarker", "detail": "MediaPipe, 21 landmarks per hand", "ready": state["jpeg"] is not None},
            {"name": "SFace", "detail": "ONNX via OpenCV DNN, 128-d face embeddings", "ready": bool(state.get("sface_ready"))},
            {"name": "Age CNN", "detail": "ONNX via OpenCV DNN, 8 age buckets", "ready": state["age_ready"]},
            {"name": "Speech-to-text", "detail": "Google Web Speech + adaptive energy VAD", "ready": not state["mic_error"]},
            {"name": "Text-to-speech", "detail": "Windows SAPI voice", "ready": True},
            {"name": "LLM brain", "detail": (provider + " (multimodal)") if provider else "No API key set", "ready": bool(provider)},
        ],
        "latencies": list(latencies),
        "db": db_stats(),
    }


def db_timeline(minutes=60):
    cutoff = (datetime.datetime.now() - datetime.timedelta(minutes=minutes)).isoformat(timespec="seconds")
    with db_lock:
        rows = db.execute("SELECT ts, fingers FROM detections WHERE ts >= ? ORDER BY ts", (cutoff,)).fetchall()
    buckets = {}
    for ts, fingers in rows:
        b = buckets.setdefault(ts[:16], {"t": ts[:16], "count": 0, "fingers": 0})
        b["count"] += 1
        b["fingers"] += fingers
    return {"minutes": minutes, "points": [buckets[k] for k in sorted(buckets)]}


def list_photos():
    d = os.path.join(folder, "photos")
    if not os.path.isdir(d):
        return []
    files = sorted((f for f in os.listdir(d) if f.lower().endswith(".jpg")), reverse=True)[:60]
    return [{"name": f, "url": "/photos/" + f} for f in files]


# ======================= API =======================
app = FastAPI(title="AI Robot")

DIST = os.path.join(folder, "frontend", "dist")  # created by: npm run build
if os.path.isdir(os.path.join(DIST, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(DIST, "assets")), name="assets")


class Text(BaseModel):
    text: str


@app.get("/", response_class=HTMLResponse)
def home():
    # 1) the built React project, 2) the single-file React page, 3) the original page
    for path in (os.path.join(DIST, "index.html"), os.path.join(folder, "dashboard.html")):
        if os.path.exists(path):
            return open(path, encoding="utf-8").read()
    return PAGE


@app.get("/classic", response_class=HTMLResponse)
def classic():
    return PAGE


@app.get("/status")
def status():
    enroll = state["enroll"]
    return {"faces": state["faces"], "fingers": state["fingers"],
            "expression": state["expression"], "mic": state["mic"], "llm": get_llm()[0],
            "person": " | ".join(t for t in (state["labels"][0] if state["labels"] else ()) if t) or "-",
            "mic_error": state["mic_error"], "history": history[-30:],
            "signals": state["signals"], "fps": round(state["fps"], 1),
            "mic_level": round(state["mic_level"], 1), "mic_threshold": round(state["mic_threshold"], 1),
            "voice_state": "speaking" if state["speaking"] else state["voice_state"],
            "voice_on": state["voice_on"],
            "enroll": ({"name": enroll["name"], "progress": len(enroll["samples"]), "total": 8}
                       if enroll else None)}


@app.get("/history")
def get_history(limit: int = 50):
    return db_history(limit)


@app.get("/stats")
def get_stats():
    return db_stats()


@app.get("/detections/summary")
def detections_summary():
    return db_detection_summary()


@app.get("/people")
def get_people():
    return {"people": list(people)}


@app.post("/history/clear")
def clear_history():
    db_clear_history()
    return {"cleared": True}


@app.get("/llm/test")
def llm_test():
    return llm_diagnose()


@app.get("/system")
def system():
    return system_info()


@app.get("/identify")
def identify():
    return identify_details()


@app.get("/detections/timeline")
def detections_timeline(minutes: int = 60):
    return db_timeline(minutes)


@app.get("/photos")
def photos():
    return list_photos()


@app.get("/photos/{name}")
def photo_file(name: str):
    path = os.path.join(folder, "photos", os.path.basename(name))
    if not os.path.isfile(path):
        return Response(status_code=404)
    return FileResponse(path, media_type="image/jpeg")


@app.post("/voice/toggle")
def voice_toggle():
    state["voice_on"] = not state["voice_on"]
    return {"voice_on": state["voice_on"]}


@app.get("/faces")
def faces():
    return {"faces": state["faces"]}


@app.get("/fingers")
def fingers():
    return {"fingers": state["fingers"]}


@app.post("/command")
def command(body: Text):
    return {"reply": respond(body.text)}


@app.post("/speak")
def speak(body: Text):
    speech_q.put(body.text)
    return {"spoken": body.text}


@app.post("/mic/toggle")
def mic_toggle():
    state["mic"] = not state["mic"]
    return {"mic": state["mic"]}


@app.get("/video")
def video():
    def gen():
        while True:
            j = state["jpeg"]
            if j:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + j + b"\r\n"
            time.sleep(0.05)
    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


PAGE = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>AI Robot Dashboard</title>
<style>
 body{margin:0;background:#0b0f14;color:#e6edf3;font-family:Segoe UI,Arial,sans-serif}
 header{padding:14px 24px;background:#111823;border-bottom:1px solid #223}
 h1{margin:0;font-size:20px}
 .wrap{display:flex;gap:20px;padding:20px;flex-wrap:wrap}
 .card{background:#111823;border:1px solid #223;border-radius:12px;padding:16px}
 #cam{width:640px;max-width:100%;border-radius:8px;display:block}
 .stats{display:flex;gap:12px;margin-top:12px}
 .stat{flex:1;text-align:center;background:#0b0f14;border-radius:8px;padding:10px}
 .stat b{display:block;font-size:32px;color:#3fb950}
 .stat b#expr,.stat b#person{font-size:20px;line-height:38px}
 .side{flex:1;min-width:300px;display:flex;flex-direction:column;gap:12px}
 button{background:#238636;color:#fff;border:0;border-radius:8px;padding:10px 14px;font-size:14px;cursor:pointer}
 button.on{background:#da3633}
 button.alt{background:#1f6feb}
 input{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;border:1px solid #334;background:#0b0f14;color:#e6edf3}
 #log{height:260px;overflow-y:auto;font-size:14px}
 .you{color:#79c0ff;margin-top:8px}.bot{color:#3fb950}
 .row{display:flex;gap:8px;flex-wrap:wrap}
</style></head><body>
<header><h1>AI Robot Dashboard <span id="brain" style="font-size:13px;font-weight:normal;color:#8b949e;margin-left:12px"></span></h1></header>
<div class="wrap">
 <div class="card">
  <img id="cam" src="/video">
  <div class="stats">
   <div class="stat"><b id="faces">0</b>Faces</div>
   <div class="stat"><b id="fingers">0</b>Fingers</div>
   <div class="stat"><b id="expr">-</b>Expression</div>
   <div class="stat"><b id="person">-</b>Person</div>
  </div>
 </div>
 <div class="side">
  <div class="card">
   <button id="micBtn" onclick="toggleMic()">Mic</button>
   <div class="row" style="margin-top:10px">
    <button class="alt" onclick="clearHistory()">Clear history</button>
    <button class="alt" onclick="send('count my fingers')">Count fingers</button>
    <button class="alt" onclick="send('how do i look')">My expression</button>
   </div>
   <div id="stats" style="margin-top:10px;font-size:13px;color:#8b949e"></div>
   <div style="margin-top:10px"><input id="txt" placeholder="Type a command (e.g. open telegram, search cats on google)"></div>
  </div>
  <div class="card"><div id="log"></div></div>
 </div>
</div>
<script>
 const $=id=>document.getElementById(id);
 const esc=s=>String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
 async function send(t){
  if(!t.trim())return;
  await fetch('/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:t})});
 }
 async function clearHistory(){await fetch('/history/clear',{method:'POST'});}
 async function loadStats(){
  try{
   const d=await (await fetch('/stats')).json();
   $('stats').textContent='Saved in database: '+d.commands+' messages, '+d.detections+' detections, '+d.people+' people'+(d.top_expression?', most common mood: '+d.top_expression:'');
  }catch(e){}
 }
 setInterval(loadStats,5000);loadStats();
 async function toggleMic(){await fetch('/mic/toggle',{method:'POST'});}
 $('txt').addEventListener('keydown',e=>{if(e.key==='Enter'){send(e.target.value);e.target.value='';}});
 async function poll(){
  try{
   const d=await (await fetch('/status')).json();
   $('faces').textContent=d.faces;
   $('fingers').textContent=d.fingers;
   $('expr').textContent=d.expression;
   $('person').textContent=d.person;
   $('brain').textContent=d.llm?('Brain: '+d.llm+' connected'):'Brain: keywords only (add api_key.txt)';
   const b=$('micBtn');
   b.textContent=d.mic_error?('Mic error: '+d.mic_error):(d.mic?'Mic ON - just talk (click to mute)':'Mic MUTED (click to start)');
   b.className=d.mic?'on':'';
   $('log').innerHTML=d.history.map(h=>'<div class="you">You: '+esc(h.you)+'</div><div class="bot">Robot: '+esc(h.robot)+'</div>').join('');
   $('log').scrollTop=$('log').scrollHeight;
  }catch(e){}
 }
 setInterval(poll,700);poll();
</script></body></html>
"""

if __name__ == "__main__":
    threading.Thread(target=speech_worker, daemon=True).start()
    threading.Thread(target=installed_apps, daemon=True).start()  # preload app list
    init_db()
    load_people()
    threading.Thread(target=log_worker, daemon=True).start()
    threading.Thread(target=ident_worker, daemon=True).start()
    threading.Thread(target=camera_worker, daemon=True).start()
    threading.Thread(target=mic_worker, daemon=True).start()
    speech_q.put("Hello, I am ready. Just talk to me.")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(app, host="127.0.0.1", port=8000)
