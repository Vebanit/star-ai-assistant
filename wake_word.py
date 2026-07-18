import os
import struct
import time
from pathlib import Path

import requests
import speech_recognition as sr
from dotenv import load_dotenv

import star_voice


BASE_URL = "http://127.0.0.1:8000"
WAKE_WORD_FILE = "Hello-STAR_en_windows_v4_0_0.ppn"

load_dotenv()

recognizer = sr.Recognizer()
recognizer.non_speaking_duration = 0.5
recognizer.dynamic_energy_threshold = True
conversation_mode = False


def apply_voice_settings(settings=None):
    settings = settings or star_voice.get_settings()
    recognizer.pause_threshold = float(settings.get("voice_pause_threshold", "0.8"))
    recognizer.energy_threshold = int(float(settings.get("voice_energy_threshold", "300")))
    return settings


def call_star(path, params=None, method="get"):
    try:
        request = requests.post if method == "post" else requests.get
        return request(f"{BASE_URL}{path}", params=params, timeout=20)
    except requests.RequestException as exc:
        print("STAR backend request failed:", exc)
        return None


def recognize_with_fallback(audio, settings, strip_wake=True):
    errors = []
    for language in star_voice.recognition_languages(settings):
        try:
            transcript = recognizer.recognize_google(audio, language=language)
            if strip_wake:
                return star_voice.clean_transcript(transcript), language
            return star_voice.normalize_text(transcript), language
        except sr.UnknownValueError:
            errors.append(language)
        except Exception as exc:
            print(f"Speech recognition error for {language}:", exc)
            errors.append(language)
    print("Not understood with languages:", ", ".join(errors))
    return "", None


def handle_spoken_command(command, used_language=None):
    global conversation_mode

    command = star_voice.clean_transcript(command)
    if not command:
        return

    language = f" ({used_language})" if used_language else ""
    print(f"You said{language}:", command)

    settings = star_voice.get_settings()
    if star_voice.is_voice_quiet(settings):
        if star_voice.is_resume_command(command):
            print("Resuming STAR voice conversation.")
            call_star("/voice/resume", method="post")
            conversation_mode = True
            return
        print("STAR is quiet. Ignoring command until resume phrase.")
        conversation_mode = False
        return

    if star_voice.is_exit_listening_command(command):
        print("Entering wake-only sleep mode.")
        call_star("/voice/sleep", method="post")
        conversation_mode = False
        return

    if star_voice.is_quiet_command(command):
        print("Putting STAR in quiet mode.")
        call_star("/voice/quiet", method="post")
        conversation_mode = False
        return

    if star_voice.is_stop_speaking_command(command):
        print("Stopping speech...")
        call_star("/stop")
        return

    if star_voice.is_repeat_command(command):
        print("Repeating last reply...")
        call_star("/voice/repeat", method="post")
        return

    confirmation = star_voice.confirmation_intent(command)
    if confirmation:
        print("Confirmation intent:", confirmation)
        call_star("/ask-star", params={"q": confirmation})
        return

    response = call_star("/ask-star", params={"q": command})
    if response is not None:
        try:
            reply = response.json().get("reply", "")
            star_voice.remember_interaction(command, reply)
        except ValueError:
            pass


def listen_continuous():
    global conversation_mode

    while conversation_mode:
        settings = apply_voice_settings()
        with sr.Microphone() as source:
            print("Listening Bajrangi...")
            recognizer.adjust_for_ambient_noise(source, duration=0.3)

            try:
                audio = recognizer.listen(
                    source,
                    timeout=int(float(settings.get("voice_timeout", "5"))),
                    phrase_time_limit=int(float(settings.get("voice_phrase_time_limit", "6"))),
                )
            except sr.WaitTimeoutError:
                continue

        command, used_language = recognize_with_fallback(audio, settings, strip_wake=True)
        handle_spoken_command(command, used_language)


def listen_for_speech_wake():
    global conversation_mode

    print("STAR is listening in free keyless wake mode...")
    print("Say: hello star, hey star, or star.")

    while True:
        settings = apply_voice_settings()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.2)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
            except sr.WaitTimeoutError:
                continue

        transcript, used_language = recognize_with_fallback(audio, settings, strip_wake=False)
        if not transcript:
            continue

        phrase = star_voice.detect_wake_phrase(transcript, settings=settings)
        if not phrase:
            continue

        print(f"Wake phrase detected: {phrase}")
        immediate_command = star_voice.command_after_wake(transcript, settings=settings)
        conversation_mode = True
        if immediate_command:
            handle_spoken_command(immediate_command, used_language)
        else:
            call_star("/voice/wake", method="post")
        listen_continuous()


def should_try_picovoice(settings):
    engine = str(settings.get("wake_engine", "auto")).lower()
    has_key = bool(os.getenv("PICOVOICE_ACCESS_KEY"))
    has_keyword = Path(WAKE_WORD_FILE).exists()
    return engine in {"auto", "picovoice"} and has_key and has_keyword


def listen_for_picovoice_wake():
    import pvporcupine
    import pyaudio

    global conversation_mode

    porcupine = pvporcupine.create(
        access_key=os.getenv("PICOVOICE_ACCESS_KEY"),
        keyword_paths=[WAKE_WORD_FILE],
    )
    pa = pyaudio.PyAudio()
    stream = None

    def open_stream():
        return pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length,
        )

    try:
        stream = open_stream()
        print("STAR is listening with Picovoice wake word...")
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                print("Wake word detected!")
                conversation_mode = True
                stream.stop_stream()
                stream.close()
                stream = None
                time.sleep(0.3)
                listen_continuous()
                stream = open_stream()
    finally:
        if stream:
            stream.close()
        pa.terminate()
        porcupine.delete()


def main():
    settings = apply_voice_settings()
    engine = str(settings.get("wake_engine", "auto")).lower()

    if should_try_picovoice(settings):
        try:
            listen_for_picovoice_wake()
            return
        except Exception as exc:
            print("Picovoice wake failed:", exc)
            if engine == "picovoice":
                raise
            print("Falling back to free keyless speech wake mode.")

    listen_for_speech_wake()


if __name__ == "__main__":
    main()
