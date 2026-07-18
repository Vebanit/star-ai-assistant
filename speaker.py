import asyncio
import os
import sys
import tempfile

import edge_tts
from dotenv import load_dotenv
from playsound import playsound


load_dotenv()

VOICE = os.getenv("STAR_TTS_VOICE", "en-US-JennyNeural")
RATE = os.getenv("STAR_TTS_RATE", "+5%")
PITCH = os.getenv("STAR_TTS_PITCH", "+0Hz")


async def make_audio(text, output_path):
    communicate = edge_tts.Communicate(
        text,
        voice=VOICE,
        rate=RATE,
        pitch=PITCH,
    )
    await communicate.save(output_path)


def main():
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        return 0

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_path = temp_file.name
    temp_file.close()

    try:
        asyncio.run(make_audio(text, temp_path))
        playsound(temp_path)
        return 0
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
