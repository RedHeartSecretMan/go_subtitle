from faster_whisper import WhisperModel

model_size = "large-v2"

model = WhisperModel(model_size)

segments, info = model.transcribe(
    "./data/test/audios/Mojito.mp3",
    beam_size=5,
)

print(
    "Detected language '%s' with probability %f"
    % (info.language, info.language_probability)
)

for segment in segments:
    print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))
