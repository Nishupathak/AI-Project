import speech_recognition as sr
import pyttsx3
import sounddevice as sd

recognizer = sr.Recognizer()
engine = pyttsx3.init()
FS = 16000  # sample rate

def speak(text):
    print("Robot:", text)
    engine.say(text)
    engine.runAndWait()

def listen(seconds=4):
    print(f"Listening for {seconds} seconds... speak now")
    recording = sd.rec(int(seconds * FS), samplerate=FS, channels=1, dtype="int16")
    sd.wait()
    audio = sr.AudioData(recording.tobytes(), FS, 2)
    try:
        text = recognizer.recognize_google(audio)
        print("You:", text)
        return text.lower()
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        speak("Internet problem")
        return ""

speak("Hello, I am ready")

while True:
    command = listen()
    if command == "":
        continue
    if "stop" in command or "exit" in command:
        speak("Goodbye")
        break
    speak("You said " + command)