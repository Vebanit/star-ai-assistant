import os
import struct
import sys
import time
import audioop
from pathlib import Path

import requests
import speech_recognition as sr
from dotenv import load_dotenv

import star_voice


BASE_URL = "http://127.0.0.1:8000"
WAKE_WORD_FILE = "Hello-STAR_en_windows_v4_0_0.ppn"
WAKE_REPLY_SETTLE_SECONDS = 1.4
FALLBACK_WAKE_COOLDOWN_SECONDS = 8.0

load_dotenv()
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    pass

recognizer = sr.Recognizer()
recognizer.non_speaking_duration = 0.25
recognizer.dynamic_energy_threshold = True
conversation_mode = False
last_fallback_wake = 0


def audio_stats(audio):
    raw = audio.get_raw_data()
    sample_width = audio.sample_width
    sample_rate = audio.sample_rate
    duration = len(raw) / max(1, sample_rate * sample_width)
    rms = audioop.rms(raw, sample_width) if raw else 0
    peak = audioop.max(raw, sample_width) if raw else 0
    return {"duration": duration, "rms": rms, "peak": peak}


def should_fallback_wake(audio, settings):
    global last_fallback_wake

    stats = audio_stats(audio)
    energy = int(float(settings.get("voice_energy_threshold", "300")))
    now = time.time()
    is_short_phrase = 0.35 <= stats["duration"] <= 4.8
    is_clear_voice = (
        stats["rms"] >= max(240, energy * 0.8) and stats["peak"] >= max(2400, energy * 7)
    ) or stats["peak"] >= max(3800, energy * 11)
    cooled_down = now - last_fallback_wake >= FALLBACK_WAKE_COOLDOWN_SECONDS
    print(
        f"Wake audio not recognized: duration={stats['duration']:.2f}s rms={stats['rms']} peak={stats['peak']}",
        flush=True,
    )
    if is_short_phrase and is_clear_voice and cooled_down:
        last_fallback_wake = now
        return True
    return False


def apply_voice_settings(settings=None):
    settings = settings or star_voice.get_settings()
    recognizer.pause_threshold = float(settings.get("voice_pause_threshold", "0.8"))
    recognizer.energy_threshold = int(float(settings.get("voice_energy_threshold", "300")))
    recognizer.non_speaking_duration = min(0.25, recognizer.pause_threshold)
    return settings


def call_star(path, params=None, method="get"):
    try:
        request = requests.post if method == "post" else requests.get
        return request(f"{BASE_URL}{path}", params=params, timeout=20)
    except requests.RequestException as exc:
        print("STAR backend request failed:", exc, flush=True)
        return None


def star_is_speaking():
    response = call_star("/voice/status")
    if response is None:
        return False
    try:
        return bool(response.json().get("is_speaking"))
    except ValueError:
        return False


def wait_for_star_to_finish_speaking(max_seconds=12):
    started = time.time()
    saw_speech = False
    while time.time() - started < max_seconds:
        if star_is_speaking():
            saw_speech = True
            time.sleep(0.2)
            continue
        if saw_speech:
            time.sleep(0.25)
        return


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
            print(f"Speech recognition error for {language}:", exc, flush=True)
            errors.append(language)
    print("Not understood with languages:", ", ".join(errors), flush=True)
    return "", None


def handle_spoken_command(command, used_language=None):
    global conversation_mode

    raw_command = star_voice.normalize_text(command)
    if star_voice.detect_wake_phrase(raw_command) and not star_voice.command_after_wake(raw_command):
        print("Wake phrase repeated in conversation mode.", flush=True)
        response = call_star("/voice/wake", method="post")
        if response is not None:
            print("Wake acknowledgement sent.", flush=True)
        time.sleep(WAKE_REPLY_SETTLE_SECONDS)
        return

    command = star_voice.clean_transcript(command)
    if not command:
        return

    language = f" ({used_language})" if used_language else ""
    print(f"You said{language}:", command, flush=True)

    settings = star_voice.get_settings()
    if star_voice.is_voice_quiet(settings):
        if star_voice.is_resume_command(command):
            print("Resuming STAR voice conversation.", flush=True)
            call_star("/voice/resume", method="post")
            conversation_mode = True
            return
        print("STAR is quiet. Ignoring command until resume phrase.", flush=True)
        conversation_mode = False
        return

    if star_voice.is_exit_listening_command(command):
        print("Entering wake-only sleep mode.", flush=True)
        call_star("/voice/sleep", method="post")
        conversation_mode = False
        return

    if star_voice.is_quiet_command(command):
        print("Putting STAR in quiet mode.", flush=True)
        call_star("/voice/quiet", method="post")
        conversation_mode = False
        return

    if star_voice.is_stop_speaking_command(command):
        print("Stopping speech...", flush=True)
        call_star("/stop")
        return

    if star_voice.is_repeat_command(command):
        print("Repeating last reply...", flush=True)
        call_star("/voice/repeat", method="post")
        return

    confirmation = star_voice.confirmation_intent(command)
    if confirmation:
        print("Confirmation intent:", confirmation, flush=True)
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

    idle_misses = 0
    while conversation_mode:
        wait_for_star_to_finish_speaking()
        settings = apply_voice_settings()
        with sr.Microphone() as source:
            print("Listening Bajrangi...", flush=True)
            recognizer.adjust_for_ambient_noise(source, duration=0.12)

            try:
                audio = recognizer.listen(
                    source,
                    timeout=int(float(settings.get("voice_timeout", "5"))),
                    phrase_time_limit=int(float(settings.get("voice_phrase_time_limit", "6"))),
                )
            except sr.WaitTimeoutError:
                idle_misses += 1
                if idle_misses >= 2:
                    print("No command heard. Returning to wake mode.", flush=True)
                    conversation_mode = False
                    return
                continue

        if star_is_speaking():
            print("Ignoring mic audio while STAR is speaking.", flush=True)
            wait_for_star_to_finish_speaking()
            continue

        command, used_language = recognize_with_fallback(audio, settings, strip_wake=False)
        if not command:
            idle_misses += 1
            if idle_misses >= 2:
                print("No clear command heard. Returning to wake mode.", flush=True)
                conversation_mode = False
                return
            continue
        idle_misses = 0
        handle_spoken_command(command, used_language)
        wait_for_star_to_finish_speaking()


def listen_for_speech_wake():
    global conversation_mode

    print("STAR is listening in free keyless wake mode...", flush=True)
    print("Say: hello star, hey star, or star.", flush=True)

    while True:
        settings = apply_voice_settings()
        with sr.Microphone() as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.1)
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
            except sr.WaitTimeoutError:
                continue

        if star_is_speaking():
            print("Ignoring wake audio while STAR is speaking.", flush=True)
            wait_for_star_to_finish_speaking()
            continue

        transcript, used_language = recognize_with_fallback(audio, settings, strip_wake=False)
        if not transcript:
            if should_fallback_wake(audio, settings):
                print("Fallback wake from short clear voice audio.", flush=True)
                conversation_mode = True
                response = call_star("/voice/wake", method="post")
                if response is not None:
                    print("Wake acknowledgement sent.", flush=True)
                time.sleep(WAKE_REPLY_SETTLE_SECONDS)
                listen_continuous()
            continue

        phrase = star_voice.detect_wake_phrase(transcript, settings=settings)
        if not phrase:
            print(f"Heard without wake phrase ({used_language}): {transcript}", flush=True)
            continue

        print(f"Wake phrase detected: {phrase}", flush=True)
        immediate_command = star_voice.command_after_wake(transcript, settings=settings)
        conversation_mode = True
        if immediate_command:
            handle_spoken_command(immediate_command, used_language)
        else:
            response = call_star("/voice/wake", method="post")
            if response is not None:
                print("Wake acknowledgement sent.", flush=True)
            time.sleep(WAKE_REPLY_SETTLE_SECONDS)
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
        print("STAR is listening with Picovoice wake word...", flush=True)
        while True:
            pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                print("Wake word detected!", flush=True)
                conversation_mode = True
                stream.stop_stream()
                stream.close()
                stream = None
                response = call_star("/voice/wake", method="post")
                if response is not None:
                    print("Wake acknowledgement sent.", flush=True)
                time.sleep(WAKE_REPLY_SETTLE_SECONDS)
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
            print("Picovoice wake failed:", exc, flush=True)
            print("Falling back to free keyless speech wake mode.", flush=True)

    listen_for_speech_wake()


if __name__ == "__main__":
    main()
