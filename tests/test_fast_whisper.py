import os
from datetime import datetime

from faster_whisper import WhisperModel


def transcribe_directory(
    input_dir,
    output_dir="transcriptions",
    model_size="large-v2",
    language_type="zh",
):
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Initialize the model once outside the loop
    model = WhisperModel(model_size_or_path=model_size)

    # Supported audio formats
    audio_extensions = (".m4a", ".mp3", ".wav", ".flac")

    # Process each audio file in the directory
    for filename in os.listdir(input_dir):
        if filename.lower().endswith(audio_extensions):
            # Full path of the audio file
            audio_path = os.path.join(input_dir, filename)

            # Create output filename (replace audio extension with .txt)
            output_filename = os.path.splitext(filename)[0] + ".txt"
            output_path = os.path.join(output_dir, output_filename)

            print(f"Processing: {filename}")

            try:
                # Transcribe the audio
                segments, info = model.transcribe(
                    audio=audio_path,
                    language=language_type,
                    beam_size=5,
                )

                # Write results to file
                with open(output_path, "w", encoding="utf-8") as f:
                    # Write header information
                    f.write(f"Transcription of: {filename}\n")
                    f.write(
                        f"Processed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )
                    f.write(
                        f"Detected language: {info.language} (probability: {info.language_probability:.2f})\n"
                    )
                    f.write("-" * 50 + "\n\n")

                    # Write transcription segments
                    for segment in segments:
                        f.write(
                            f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}\n"
                        )

                print(f"Completed: {filename} -> {output_filename}")

            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")

    print("\nTranscription complete!")


if __name__ == "__main__":
    input_directory = "/Users/WangHao/Downloads/audios"
    transcribe_directory(input_directory)
