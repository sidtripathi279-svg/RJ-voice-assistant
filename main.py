import speech_recognition as sr
import pyttsx3
import pyautogui
import webbrowser
import subprocess
import os
import google.generativeai as genai
import time

# ---------------- AI SETUP ---------------- #
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-pro")

# ---------------- VOICE ---------------- #
engine = pyttsx3.init()
engine.setProperty("rate", 170)

def speak(text):
    print("RJ:", text)
    engine.say(text)
    engine.runAndWait()

# ---------------- LISTEN ---------------- #
r = sr.Recognizer()

def listen():
    try:
        with sr.Microphone() as source:
            print("🎤 Listening...")
            r.adjust_for_ambient_noise(source, duration=1)
            audio = r.listen(source, timeout=6, phrase_time_limit=6)

        text = r.recognize_google(audio, language="en-IN")
        print("🗣 You said:", text)
        return text.lower()

    except sr.WaitTimeoutError:
        print("⏰ Timeout")
        return ""
    except sr.UnknownValueError:
        print("❌ Could not understand")
        return ""
    except Exception as e:
        print("ERROR:", e)
        return ""

# ---------------- SYSTEM COMMANDS ---------------- #
def open_app(app):
    subprocess.call(["open", "-a", app])

def system_commands(cmd):
    if "youtube" in cmd:
        webbrowser.open("https://youtube.com")
        speak("Opening YouTube")
        return True

    if "play song" in cmd:
        song = cmd.replace("play song", "").strip()
        url = f"https://www.youtube.com/results?search_query={song.replace(' ', '+')}"
        webbrowser.open(url)
        speak(f"Playing {song}")
        return True

    if "chrome" in cmd:
        open_app("Google Chrome")
        speak("Opening Chrome")
        return True

    if "volume up" in cmd:
        pyautogui.press("volumeup")
        speak("Volume increased")
        return True

    if "volume down" in cmd:
        pyautogui.press("volumedown")
        speak("Volume decreased")
        return True

    if "screenshot" in cmd:
        name = f"screenshot_{int(time.time())}.png"
        pyautogui.screenshot(name)
        speak("Screenshot taken")
        return True

    if "exit" in cmd or "stop" in cmd or "band karo" in cmd:
        speak("Shutting down. Bye Siddharth")
        exit()

    return False

# ---------------- AI BRAIN ---------------- #
def ai_answer(question):
    try:
        response = model.generate_content(question)
        return response.text
    except:
        return "Sorry, I could not answer right now."

# ---------------- MAIN ---------------- #
def main():
    speak("RJ standby mode is on")

    while True:
        command = listen()

        if not command:
            continue

        handled = system_commands(command)

        if not handled:
            speak("Thinking")
            answer = ai_answer(command)
            speak(answer)

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        speak("Program stopped")
