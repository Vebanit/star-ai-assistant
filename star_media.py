import random
import subprocess
import webbrowser
from urllib.parse import quote_plus

import pyautogui


SAD_SONGS = {
    "hindi": [
        ("Channa Mereya", "284Ov7ysmfA"),
        ("Agar Tum Saath Ho", "sK7riqg2mr4"),
        ("Tum Hi Ho", "IJq0yyWug1k"),
    ],
    "english": [
        ("Someone Like You", "hLQl3WQQoQ0"),
        ("Let Her Go", "RBumgq5yVrA"),
        ("Fix You", "k4V3Mo61fJM"),
    ],
}

GENERIC_SONGS = [
    ("Hindi hits mix", "https://www.youtube.com/results?search_query=popular+hindi+songs+playlist"),
    ("English hits mix", "https://www.youtube.com/results?search_query=popular+english+songs+playlist"),
    ("Lo-fi music live", "https://www.youtube.com/watch?v=jfKfPfyJRdk&autoplay=1"),
]


def play_pause():
    pyautogui.press("playpause")
    return "Toggled play or pause."


def next_track():
    pyautogui.press("nexttrack")
    return "Next track."


def previous_track():
    pyautogui.press("prevtrack")
    return "Previous track."


def stop_media():
    pyautogui.press("stop")
    return "Stopped media."


def play_youtube_video(video_id):
    webbrowser.open(f"https://www.youtube.com/watch?v={video_id}&autoplay=1")


def play_sad_song(language):
    clean_language = "hindi" if str(language).lower().startswith("hin") else "english"
    title, video_id = random.choice(SAD_SONGS[clean_language])
    play_youtube_video(video_id)
    return f"Playing a {clean_language} sad song: {title}."


def play_generic_song(query=None):
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query + ' song')}")
        return f"Playing songs for {query} on YouTube."

    title, url = random.choice(GENERIC_SONGS)
    webbrowser.open(url)
    return f"Playing {title} on YouTube."


def open_youtube(query=None):
    if query:
        webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
        return f"Searching YouTube for {query}."

    webbrowser.open("https://www.youtube.com")
    return "Opening YouTube."


def open_spotify(query=None):
    try:
        subprocess.Popen('start "" spotify:', shell=True)
        if query:
            return f"Opening Spotify. Search for {query} when it opens."
        return "Opening Spotify."
    except Exception:
        webbrowser.open("https://open.spotify.com")
        return "Opening Spotify web."


def open_netflix():
    webbrowser.open("https://www.netflix.com")
    return "Opening Netflix."


def open_vlc():
    try:
        subprocess.Popen('start "" vlc', shell=True)
        return "Opening VLC."
    except Exception:
        return "VLC was not found."


def handle_media_command(command):
    text = command.lower().strip()

    if "sad" in text and any(word in text for word in ["song", "music", "gaana", "gana"]):
        if any(word in text for word in ["hindi", "hindee"]):
            return play_sad_song("hindi")
        if any(word in text for word in ["english", "angrezi"]):
            return play_sad_song("english")
        return "Hindi ya English?"

    if "youtube" in text:
        query = text.replace("open youtube", "").replace("play youtube", "").replace("youtube", "").strip()
        return open_youtube(query or None)

    if "spotify" in text:
        query = text.replace("open spotify", "").replace("play spotify", "").replace("spotify", "").strip()
        return open_spotify(query or None)

    if "netflix" in text:
        return open_netflix()

    if "vlc" in text:
        return open_vlc()

    if any(word in text for word in ["song", "gaana", "gana"]) and any(word in text for word in ["play", "chala", "chalao", "chalana", "baja", "lagao"]):
        query = text
        for phrase in ["play", "song", "songs", "gaana", "gana", "chalao", "chalana", "chala", "baja", "lagao", "please"]:
            query = query.replace(phrase, " ")
        query = " ".join(query.split())
        return play_generic_song(query or None)

    if "music" in text and any(word in text for word in ["play", "chala", "chalao", "chalana", "baja", "lagao"]):
        return play_generic_song()

    if any(phrase in text for phrase in ["play pause", "pause music", "pause media", "resume media"]):
        return play_pause()

    if any(phrase in text for phrase in ["next song", "next track", "next media"]):
        return next_track()

    if any(phrase in text for phrase in ["previous song", "previous track", "prev song"]):
        return previous_track()

    if any(phrase in text for phrase in ["stop music", "stop media"]):
        return stop_media()

    return None
