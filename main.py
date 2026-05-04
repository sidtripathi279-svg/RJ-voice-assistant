import os
import time
import datetime
import subprocess
import requests
import speech_recognition as sr
import pyttsx3
from groq import Groq
import sounddevice as sd
import numpy as np
import re

# ================= CONFIG =================
WAKE_WORDS = ["hello rj", "hey rj", "hi rj", "hello r", "hey r", "hi r"]
SESSION_SECONDS = 120  # 2 minutes
import os
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# ================= STATE FLAGS =================
PENDING_DELETE_FOLDER = None
WAITING_CONFIRMATION = False
PENDING_FILE_NAME = None   # ✅ ADD THIS LINE
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "You are RJ, a smart Mac voice assistant. "
        "Reply concisely. Use simple English or Hinglish. "
        "Do not ask unnecessary questions ")}
# ================= GROQ =================
client = Groq(api_key=GROQ_API_KEY)

# ================= TTS =================
engine = pyttsx3.init(driverName="nsss")
engine.setProperty("rate", 175)
IS_SPEAKING = False  # 🔒 mic lock
def speak(text: str):
    global IS_SPEAKING
    try:
        IS_SPEAKING = True
        text = text[:180]
        print("RJ:", text)

        engine.stop()      # 🔥 important
        engine.say(text)
        engine.runAndWait()

    except Exception as e:
        print("TTS error:", e)

    finally:
        IS_SPEAKING = False
        time.sleep(0.3)   # 🔒 mic cool-down
# ================= MIC =================

RECOGNIZER = sr.Recognizer()
RECOGNIZER.energy_threshold = 300
RECOGNIZER.dynamic_energy_threshold = True

SAMPLE_RATE = 16000


def run_shortcut(name):
    subprocess.run(["shortcuts", "run", name])


def listen(timeout=5):
    time.sleep(0.15)
    if IS_SPEAKING:
        time.sleep(0.2)
        return ""

    try:
        print("🎤 Listening...")
        audio = sd.rec(
            int(timeout * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16"
        )
        sd.wait()

        audio = np.squeeze(audio)

        audio_data = sr.AudioData(
            audio.tobytes(),
            SAMPLE_RATE,
            2
        )

        try:
            text = RECOGNIZER.recognize_google(
                audio_data,
                language="en-IN"
            )
            text = text.lower().strip()
            print("YOU:", text)
            return text

        except sr.RequestError:
            # 🔌 Internet / Google issue
            print("⚠️ Network issue (STT)")
            return ""

        except sr.UnknownValueError:
            # 🤷 Samajh nahi aaya
            return ""

    except KeyboardInterrupt:
        raise SystemExit

    except Exception as e:
        print("Mic error:", e)
        return ""


# ================= APP MAP =================
def get_weather_any_city(city):
    try:
        geo_url = (
            "https://nominatim.openstreetmap.org/search"
            f"?q={city}&format=json&limit=1"
        )

        geo_resp = requests.get(
            geo_url,
            headers={"User-Agent": "RJ-Assistant"},
            timeout=5
        ).json()

        if not geo_resp:
            return f"{city} ka location nahi mila"

        lat = geo_resp[0]["lat"]
        lon = geo_resp[0]["lon"]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}&current_weather=true"
        )

        weather = requests.get(weather_url, timeout=5).json()
        current = weather["current_weather"]

        temp = current["temperature"]
        wind = current["windspeed"]

        return (
            f"{city.title()} me temperature {temp} degree Celsius hai "
            f"aur hawa ki raftaar {wind} kilometer per hour hai"
        )

    except:
        return "Weather fetch nahi ho pa raha"


def get_all_mac_apps():
    app_dirs = [
        "/Applications",
        "/System/Applications",
        os.path.expanduser("~/Applications")
    ]

    apps = {}

    for directory in app_dirs:
        if not os.path.exists(directory):
            continue

        for item in os.listdir(directory):
            if item.endswith(".app"):
                key = item.replace(".app", "").lower()
                apps[key] = item.replace(".app", "")

    return apps


APP_MAP = get_all_mac_apps()

# 🎵 APPLE MUSIC CONTROLS (FINAL)


def music_play():
    subprocess.run(["osascript", "-e", 'tell application "Music" to play'])


def music_pause():
    subprocess.run(["osascript", "-e", 'tell application "Music" to pause'])


def music_next():
    subprocess.run(["osascript", "-e", 'tell application "Music" to next track'])


def music_previous():
    subprocess.run(["osascript", "-e", 'tell application "Music" to previous track'])


def music_quit():
    subprocess.run(["osascript", "-e", 'tell application "Music" to quit'])


# ================= APPLE MUSIC – PLAY BY SINGER =================


def normalize_cmd(cmd):
    cmd = cmd.lower()

    # bluetooth variations
    cmd = cmd.replace("blue tooth", "bluetooth")

    # extra symbols
    cmd = cmd.replace("-", " ")

    # clean spaces
    while "  " in cmd:
        cmd = cmd.replace("  ", " ")

    return cmd.strip()


def site_to_url(site):
    site = site.lower().strip()

    for w in ["website", "site", "page"]:
        site = site.replace(w, "")

    site = site.replace(" ", "")

    if site.startswith("http"):
        return site

    if "." in site:
        return f"https://{site}"

    if site.endswith("india"):
        return f"https://www.{site.replace('india', '')}.in"
    return f"https://www.{site}.com"


def open_any_website(site):
    url = site_to_url(site)

    script = f'''
                tell application "Safari"
                    activate
                    if (count of windows) = 0 then
                        make new document
                    end if
                    tell window 1
                        set current tab to (make new tab with properties {{URL:"{url}"}})
                    end tell
                end tell
                '''
    subprocess.run(["osascript", "-e", script])
    speak(f"{site} Safari me khol raha hoon")


def close_any_website(site):
    site = site.replace(" ", "").lower()

    script = f'''
                tell application "Safari"
                    if (count of windows) > 0 then
                        tell window 1
                            repeat with t in tabs
                                if URL of t contains "{site}" then
                                    close t
                                    exit repeat
                                end if
                            end repeat
                        end tell
                    end if
                end tell
                '''
    subprocess.run(["osascript", "-e", script])
    speak(f"{site} band kar diya")


IMPORTANT_KEYWORDS = [
    "wifi", "bluetooth", "open", "close", "play",
    "pause", "volume", "shutdown", "restart",
    "sleep", "lock", "folder", "music",
    "youtube", "google", "wikipedia", "instagram"
]


def close_finder_windows():
    script = '''
    tell application "Finder"
        close every window
    end tell
    '''
    subprocess.run(["osascript", "-e", script])


def intent_confidence(cmd):
    words = cmd.split()
    matches = sum(1 for w in words if w in IMPORTANT_KEYWORDS)

    confidence = matches / max(len(words), 1)
    return confidence
def folder_system(cmd):
    global PENDING_DELETE_FOLDER, WAITING_CONFIRMATION

    # 📂 OPEN FOLDER
    if "open folder" in cmd:
        folder = cmd.replace("open folder", "").strip()
        paths = [
            os.path.expanduser("~/"),
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads"),
            os.path.expanduser("~/Pictures"),
            os.path.expanduser("~/Movies")
        ]

        for base in paths:
            path = os.path.join(base, folder)
            if os.path.isdir(path):
                subprocess.run(["open", path])
                speak(f"{folder} folder khol diya")
                return True

        speak("Folder nahi mila")
        return True

    # ❌ CLOSE FOLDER
    if "close folder" in cmd or "band folder" in cmd:
        folder = cmd.replace("close folder", "").replace("band folder", "").strip()
        subprocess.run([
            "osascript", "-e",
            f'''
            tell application "Finder"
                repeat with w in windows
                    if name of w contains "{folder}" then close w
                end repeat
            end tell
            '''
        ])
        speak(f"{folder} folder band kar diya")
        return True

    # 📁 CREATE FOLDER
    if any(x in cmd for x in ["create folder", "make folder", "new folder"]):
        folder_name = (
            cmd.replace("create folder", "")
               .replace("make folder", "")
               .replace("new folder", "")
               .strip()
        )

        if not folder_name:
            speak("Folder ka naam batao")
            return True

        base_path = os.path.expanduser("~/Documents")
        folder_path = os.path.join(base_path, folder_name)

        if os.path.exists(folder_path):
            speak("Ye folder pehle se maujood hai")
            return True

        os.makedirs(folder_path)
        speak(f"{folder_name} folder bana diya")
        subprocess.run(["open", folder_path])
        return True

    # 🗑️ DELETE FOLDER (CONFIRMATION)
    if any(x in cmd for x in [
        "delete folder",
        "delete a folder",
        "remove folder",
        "remove a folder",
        "folder delete"
    ]):
        folder_name = (
            cmd.replace("delete a folder", "")
            .replace("delete folder", "")
            .replace("remove a folder", "")
            .replace("remove folder", "")
            .replace("folder delete", "")
            .strip()
        )

        if not folder_name:
            speak("Kaunsa folder delete karna hai")
            return True

        PENDING_DELETE_FOLDER = folder_name
        WAITING_CONFIRMATION = True
        speak(f"Kya tum sure ho {folder_name} folder delete karna hai? yes ya no bolo")
        return True

    # ✅ CONFIRM DELETE
    if WAITING_CONFIRMATION and any(x in cmd for x in ["yes", "yess","haan", "ha","haan", "confirm","ok""yes", "yas", "yess", "yep", "ya",
            "haan", "ha", "haan ji", "yes ji",
            "confirm", "ok", "okay",
            "delete kar do", "delete karo", "kar do"]):
        search_paths = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads")
        ]

        for base in search_paths:
            folder_path = os.path.join(base, PENDING_DELETE_FOLDER)
            if os.path.isdir(folder_path):
                import shutil
                shutil.rmtree(folder_path)
                speak(f"{PENDING_DELETE_FOLDER} folder delete kar diya")
                break
        else:
            speak("Folder nahi mila")

        PENDING_DELETE_FOLDER = None
        WAITING_CONFIRMATION = False
        return True

    # ❌ CANCEL DELETE
    if WAITING_CONFIRMATION and any(x in cmd for x in [
        "no", "nahi", "cancel", "mat karo"
        ]):

        speak("Delete cancel kar diya")
        PENDING_DELETE_FOLDER = None
        WAITING_CONFIRMATION = False
        return True

def file_system(cmd):
    global PENDING_FILE_NAME

    # 📝 CREATE FILE
    if cmd in ["create file", "create a file", "make file", "new file"]:
        PENDING_FILE_NAME = ""
        speak("File ka naam bolo")
        return True

    # 📝 FILE NAME GIVEN
    if PENDING_FILE_NAME == "" and cmd:
        filename = cmd.replace(" ", "_")

        if not filename.endswith(".txt"):
            filename += ".txt"

        path = os.path.join(os.path.expanduser("~/Desktop"), filename)

        if os.path.exists(path):
            speak("Ye file pehle se maujood hai")
        else:
            with open(path, "w") as f:
                f.write("")
            speak(f"File {filename} Desktop par bana di")

        subprocess.run(["open", "-R", path])
        PENDING_FILE_NAME = None
        return True


# 🔊 VOLUME HELPERS (ADD ABOVE system_command)

def set_volume(percent):
    percent = max(0, min(100, int(percent)))
    subprocess.run(
        ["osascript", "-e", f"set volume output volume {percent}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def volume_up():
    current = subprocess.check_output(
        ["osascript", "-e", "output volume of (get volume settings)"],
        text=True
    ).strip()
    set_volume(min(100, int(current) + 10))


def volume_down():
    current = subprocess.check_output(
        ["osascript", "-e", "output volume of (get volume settings)"],
        text=True
    ).strip()
    set_volume(max(0, int(current) - 10))

    # 🔊 VOLUME % EXTRACTOR (ADD ABOVE system_command)

def extract_volume_percent(cmd):
    match = re.search(r'(\d{1,3})\s*%', cmd)
    if match:
        val = int(match.group(1))
        if 0 <= val <= 100:
            return val
    return None

    return False
# ================= SYSTEM COMMANDS =================
def system_command(cmd):
    global PENDING_DELETE_FOLDER, WAITING_CONFIRMATION
    cmd = normalize_cmd(cmd)

    # 🔊 SET VOLUME BY PERCENT (SMART)
    percent = extract_volume_percent(cmd)
    if percent is not None:
        set_volume(percent)
        speak(f"Volume {percent}% kar diya")
        return True

    # 📁 HANDLE FOLDER SYSTEM
    if file_system(cmd):
        return True

    if folder_system(cmd):
        return True
    # 🚫 BLOCK AI FILE/FOLDER CONFUSION
    if any(x in cmd for x in ["rename", "untitled"]):
        speak("Exact command bolo jaise: create folder test")
        return True

    # 🔧 SETTINGS FIX
    if cmd in ["open setting", "open settings"]:
        subprocess.run(["open", "-a", "System Settings"])
        speak("Settings khol raha hoon")
        return True

    if cmd in ["close setting", "close settings"]:
        subprocess.run([
            "osascript", "-e",
            'tell application "System Settings" to quit'
        ])
        speak("Settings band kar diya")
        return True
    if "close finder" in cmd or "band finder" in cmd:
        close_finder_windows()
        speak("Finder band kar diya")
        return True
    # ❌ CLOSE APP
    if cmd.startswith("close ") or cmd.startswith("band "):
        clean = (
            cmd.replace("close", "")
            .replace("band", "")
            .replace("app", "")
            .replace("the", "")
            .strip()
        )

        for key, app_name in APP_MAP.items():
            if key in clean:

                # 🔥 WHATSAPP SPECIAL CASE (SAFE)
                if app_name.lower() == "whatsapp":
                    script = '''
                    tell application "WhatsApp"
                        activate
                        delay 0.3
                    end tell
                    tell application "System Events"
                        keystroke "q" using {command down}
                    end tell
                    '''
                    subprocess.run(["osascript", "-e", script])
                    speak("WhatsApp band kar diya")
                    return True

                # ✅ ALL OTHER APPS
                subprocess.run([
                    "osascript", "-e",
                    f'tell application "{app_name}" to quit'
                ])
                speak(f"{app_name} band kar diya")
                return True

        # 🌐 agar app nahi mila → website close
        if clean:
            close_any_website(clean)
            return True

    # 🔓 OPEN APP
    if "open" in cmd:
        for key, app_name in APP_MAP.items():
            if key in cmd:
                subprocess.run(["open", "-a", app_name])
                speak(f"{app_name} khol raha hoon")
                return True
        if "open finder" in cmd:
            subprocess.run(["open", "-a", "Finder"])
            speak("Finder khol raha hoon")
            return True
        # 🌐 OPEN ANY WEBSITE (AFTER app check)
    if cmd.startswith("open "):
        site = cmd.replace("open", "").strip()
        if site:
            open_any_website(site)
            return True

    # 🔵 OPEN BLUETOOTH SETTINGS
    if cmd == "open bluetooth":
        subprocess.run(["open", "x-apple.systempreferences:com.apple.Bluetooth"])
        speak("Bluetooth settings khol raha hoon")
        return True
        # 🔵 BLUETOOTH OFF
    if any(x in cmd for x in ["bluetooth off", "blue tooth off", "turn off bluetooth"]):
        subprocess.run(["blueutil", "--power", "0"])
        speak("Bluetooth band kar diya")
        return True

    # 🔵 BLUETOOTH ON
    if any(x in cmd for x in ["bluetooth on", "blue tooth on", "turn on bluetooth"]):
        subprocess.run(["blueutil", "--power", "1"])
        speak("Bluetooth chalu kar diya")
        return True

    # 🔊 VOLUME CONTROL (FIXED)

    if "volume up" in cmd or "volume badhao" in cmd:
        volume_up()
        speak("Volume badha diya")
        return True

    if "volume down" in cmd or "volume kam karo" in cmd:
        volume_down()
        speak("Volume kam kar diya")
        return True

    if "mute" in cmd:
        subprocess.run(["osascript", "-e", "set volume with output muted"])
        speak("Volume mute kar diya")
        return True

    if "full volume" in cmd or "max volume" in cmd:
        set_volume(100)
        speak("Volume full kar diya")
        return True

    # 🌦️ WEATHER (ANY CITY)
    if "weather" in cmd or "mausam" in cmd:
        words = cmd.replace("weather", "").replace("mausam", "").strip()

        if words == "":
            city = "delhi"
        else:
            city = words

        weather = get_weather_any_city(city)
        speak(weather)
        return True


    # 🔍 OTHER SYSTEM COMMANDS

    if "settings" in cmd:
        subprocess.run(["open", "-a", "System Settings"])
        speak("Settings khol raha hoon")
        return True

    if "time" in cmd:
        speak(datetime.datetime.now().strftime("Time %H:%M"))
        return True

    if "date" in cmd:
        speak(datetime.datetime.now().strftime("Date %d %B %Y"))
        return True

    if "exit" in cmd or "quit" in cmd:
        speak("Bye")
        engine.stop()
        exit()

    # 📂 VOICE FILE SEARCH
    if any(x in cmd for x in ["find file", "search file", "open file", "find pdf"]):
        file_name = (
            cmd.replace("find file", "")
            .replace("search file", "")
            .replace("open file", "")
            .replace("find pdf", "")
            .strip()
        )

        if not file_name:
            speak("Kaunsi file dhundhni hai")
            return True

        search_dirs = [
            os.path.expanduser("~/Desktop"),
            os.path.expanduser("~/Documents"),
            os.path.expanduser("~/Downloads")
        ]

        found_files = []

        for base in search_dirs:
            for root, dirs, files in os.walk(base):
                for file in files:
                    if file_name.lower() in file.lower():
                        found_files.append(os.path.join(root, file))
        if found_files:
            subprocess.run(["open", "-R", found_files[0]])
            speak(f"{file_name} file mil gayi, Finder me dikha raha hoon")
        else:
            speak(f"{file_name} naam ki koi file nahi mili")
        return True
    # 🎵 APPLE MUSIC CONTROL (FINAL)

    if any(x in cmd for x in ["pause music", "pause", "ruk", "rok"]):
        music_pause()
        speak("Music pause kar diya")
        return True

    if any(x in cmd for x in ["play music", "resume music"]):
        music_play()
        speak("Music play ho raha hai")
        return True

    if "next song" in cmd or "next music" in cmd:
        music_next()
        speak("Next song chala raha hoon")
        return True

    if "previous song" in cmd or "back song" in cmd:
        music_previous()
        speak("Previous song chala raha hoon")
        return True

    if "close music" in cmd or "close music app" in cmd:
        music_quit()
        speak("Music band kar diya")
        return True

    # 🔋 BATTERY PERCENTAGE
    if any(x in cmd for x in ["battery", "battery percentage", "power status", "kitni battery"]):
        try:
            output = subprocess.check_output(
                ["pmset", "-g", "batt"],
                text=True
            )

            # Example output:
            # Now drawing from 'Battery Power'
            #  -InternalBattery-0 (id=1234567)   87%; discharging; 3:12 remaining

            percent = ""
            for line in output.splitlines():
                if "%" in line:
                    percent = line.split("%")[0].split()[-1]
                    break

            if percent:
                speak(f"Battery {percent} percent hai")
            else:
                speak("Battery status nahi mil pa raha")

            return True
        except:
            speak("Battery check nahi ho pa raha")
            return True

    # 🔒 LOCK SCREEN
    if any(x in cmd for x in ["lock screen", "screen lock", "lock"]):
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to keystroke "q" using {control down, command down}'
        ])
        speak("Screen lock kar diya")
        return True

    # 💤 SLEEP
    if any(x in cmd for x in ["sleep", "sleep mode", "so jao"]):
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to sleep'
        ])
        speak("Mac sleep mode mein ja raha hai")
        return True

    # 🔄 RESTART
    if any(x in cmd for x in ["restart", "reboot"]):
        speak("Mac restart ho raha hai")
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to restart'
        ])
        return True

    # 🔴 SHUTDOWN
    if any(x in cmd for x in ["shutdown", "shut down", "band kar do", "power off"]):
        speak("Mac shutdown ho raha hai")
        subprocess.run([
            "osascript", "-e",
            'tell application "System Events" to shut down'
        ])
        return True
    # 🔍 OTHER SYSTEM COMMANDS

    if "settings" in cmd:
        subprocess.run(["open", "-a", "System Settings"])
        speak("Settings khol raha hoon")
        return True

    if "time" in cmd:
        speak(datetime.datetime.now().strftime("Time %H:%M"))
        return True

    if "date" in cmd:
        speak(datetime.datetime.now().strftime("Date %d %B %Y"))
        return True

    if "exit" in cmd or "quit" in cmd:
        speak("Bye")
        engine.stop()
        exit()
    # 🚫 BLOCK vague file/folder talk (not delete/create)
    if any(x in cmd for x in ["folder", "file"]) and not any(
            k in cmd for k in ["create", "delete", "remove", "open"]
    ):
        speak("Exact command bolo jaise: create folder test")
        return True

    return False


# ================= AI CHAT =================
CHAT_HISTORY = []


def ai_chat(text: str) -> str:
    global CHAT_HISTORY
    if not CHAT_HISTORY:
        CHAT_HISTORY.append(SYSTEM_PROMPT)

    CHAT_HISTORY.append({"role": "user", "content": text})
    CHAT_HISTORY = CHAT_HISTORY[-6:]

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=CHAT_HISTORY,
            timeout=3
        )
        reply = resp.choices[0].message.content[:180]
        CHAT_HISTORY.append({"role": "assistant", "content": reply})
        CHAT_HISTORY = CHAT_HISTORY[-6:]
        return reply
    except:
        return "Network issue hai"


# ================= MAIN =================
speak("RJ standby mode is on")

while True:
    cmd = listen(timeout=6)

    if not cmd:
        time.sleep(0.5)
        continue

    # ✅ wake word check (sirf session start ke liye)
    if not any(w in cmd for w in WAKE_WORDS):
        continue

    speak("yes sir")
    CHAT_HISTORY.clear()
    start = time.time()

    # 🔁 SESSION MODE (no wake word needed here)
    while time.time() - start < SESSION_SECONDS:
        cmd = listen(timeout=6)

        if not cmd:
            time.sleep(0.2)
            continue

        if cmd in ["exit", "quit", "stop"]:
            speak("Bye")
            raise SystemExit

        # 🔒 If waiting for delete confirmation, never go to AI
        if WAITING_CONFIRMATION:
            system_command(cmd)
            continue

        if intent_confidence(cmd) < 0.15 and "create folder" not in cmd:
            speak(ai_chat(cmd))
            continue

        if not system_command(cmd):
            speak(ai_chat(cmd))
