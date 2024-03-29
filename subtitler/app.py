import os
import torch
import ffmpeg
from .weight import load_model, available_models
from .tokenizer import LANGUAGES, TO_LANGUAGE_CODE
from .transcribe import transcribe
from .utils import str2bool, optional_int, optional_float, get_writer
from typing import Union, Tuple
import numpy as np
import argparse
import warnings
import tempfile
import filetype


def get_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # 核心参数 - 输入输出路径设置
    parser.add_argument(
        "--input_dir",
        "-i",
        type=str,
        default=None,
        nargs="*",
        help="audios or videos file directory(file parent folder or itself) to process",
    )
    parser.add_argument(
        "--output_dir",
        "-o",
        type=str,
        default="./result",
        help="directory to save the outputs; default is ./result in cwd",
    )

    # 可选参数 - 字幕、音频和视频设置
    parser.add_argument(
        "--outsubtitle_format",
        "-osf",
        type=str,
        default="all",
        choices=["txt", "vtt", "srt", "tsv", "json", "all"],
        help="format of the output subtitle file; default all available formats will be produced",
    )
    parser.add_argument(
        "--outaudio_format",
        "-oaf",
        type=str,
        default="wav",
        help="format for the output audio",
    )
    parser.add_argument(
        "--outvideo_addsubtitle_format",
        "-ovasf",
        type=str,
        default="srt",
        choices=["srt", "vtt"],
        help="format for adding subtitles to the output video",
    )
    parser.add_argument(
        "--outvideo_format",
        "-ovf",
        type=str,
        default="mp4",
        help="format of the output video",
    )
    parser.add_argument(
        "--outaudio_invideo",
        "-oaiv",
        type=str2bool,
        default=False,
        help="whether to output audio from the video",
    )
    parser.add_argument(
        "--outvideo_addsubtitle",
        "-ovas",
        type=str2bool,
        default=True,
        help="whether to output the video with subtitles",
    )
    parser.add_argument(
        "--word_timestamps",
        type=str2bool,
        default=False,
        help="(experimental) extract word-level timestamps and refine the results based on them",
    )
    parser.add_argument(
        "--highlight_words",
        type=str2bool,
        default=False,
        help="(requires --word_timestamps True) underline each word as it is spoken in srt and vtt",
    )
    parser.add_argument(
        "--max_line_width",
        type=optional_int,
        default=None,
        help="(requires --word_timestamps True) the maximum number of characters in a line before breaking the line",
    )
    parser.add_argument(
        "--max_line_count",
        type=optional_int,
        default=None,
        help="(requires --word_timestamps True) the maximum number of lines in a segment",
    )
    parser.add_argument(
        "--max_words_per_line",
        type=optional_int,
        default=None,
        help="(requires --word_timestamps True, no effect with --max_line_width) the maximum number of words in a segment",
    )

    # 可选参数 - 模型设置
    parser.add_argument(
        "--model_name",
        "-mn",
        default="base",
        type=str,
        help=f"input model's local file path or remote file proxy (in {available_models()})",
    )
    parser.add_argument(
        "--model_dir",
        type=str,
        default=None,
        help="the path to save model files; uses ~/.cache/whisper by default",
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="device to use for PyTorch inference",
    )
    parser.add_argument(
        "--language",
        type=str,
        default=None,
        choices=sorted(LANGUAGES.keys())
        + sorted([k.title() for k in TO_LANGUAGE_CODE.keys()]),
        help="language spoken in the audio, specify None to perform language detection",
    )
    parser.add_argument(
        "--temperature", type=float, default=0, help="temperature to use for sampling"
    )
    parser.add_argument(
        "--temperature_increment_on_fallback",
        type=optional_float,
        default=0.2,
        help="temperature to increase when falling back when the decoding fails to meet either of the thresholds below",
    )
    parser.add_argument(
        "--threads",
        type=optional_int,
        default=None,
        help="use torch set cpu inference number of threads, default use MKL and OMP auto set",
    )
    parser.add_argument(
        "--fp16",
        type=str2bool,
        default=True,
        help="whether to perform inference in fp16; True by default",
    )
    parser.add_argument(
        "--best_of",
        type=optional_int,
        default=5,
        help="number of candidates when sampling with non-zero temperature",
    )
    parser.add_argument(
        "--beam_size",
        type=optional_int,
        default=5,
        help="number of beams in beam search, only applicable when temperature is zero",
    )
    parser.add_argument(
        "--patience",
        type=float,
        default=None,
        help="optional patience value to use in beam decoding, as in https://arxiv.org/abs/2204.05424, the default (1.0) is equivalent to conventional beam search",
    )
    parser.add_argument(
        "--length_penalty",
        type=float,
        default=None,
        help="optional token length penalty coefficient (alpha) as in https://arxiv.org/abs/1609.08144, uses simple length normalization by default",
    )
    parser.add_argument(
        "--suppress_tokens",
        type=str,
        default="-1",
        help="comma-separated list of token ids to suppress during sampling; '-1' will suppress most special characters except common punctuations",
    )
    parser.add_argument(
        "--initial_prompt",
        type=str,
        default=None,
        help="optional text to provide as a prompt for the first window.",
    )
    parser.add_argument(
        "--condition_on_previous_text",
        type=str2bool,
        default=True,
        help="if True, provide the previous output of the model as a prompt for the next window; disabling may make the text inconsistent across windows, but the model becomes less prone to getting stuck in a failure loop",
    )
    parser.add_argument(
        "--compression_ratio_threshold",
        type=optional_float,
        default=2.4,
        help="if the gzip compression ratio is higher than this value, treat the decoding as failed",
    )
    parser.add_argument(
        "--logprob_threshold",
        type=optional_float,
        default=-1.0,
        help="if the average log probability is lower than this value, treat the decoding as failed",
    )
    parser.add_argument(
        "--no_speech_threshold",
        type=optional_float,
        default=0.6,
        help="if the probability of the <|nospeech|> token is higher than this value AND the decoding has failed due to `logprob_threshold`, consider the segment as silence",
    )
    parser.add_argument(
        "--prepend_punctuations",
        type=str,
        default="\"'“¿([{-",
        help="if word_timestamps is True, merge these punctuation symbols with the next word",
    )
    parser.add_argument(
        "--append_punctuations",
        type=str,
        default="\"'.。,，!！?？:：”)]}、",
        help="if word_timestamps is True, merge these punctuation symbols with the previous word",
    )
    parser.add_argument(
        "--verbose",
        type=str2bool,
        default=False,
        help="Whether to display model decoded output text in the console",
    )

    # 可选参数 - 任务设置
    parser.add_argument(
        "--task",
        type=str,
        default="transcribe",
        choices=["transcribe", "translate"],
        help="whether to perform X->X speech recognition ('transcribe') or X->English translation ('translate')",
    )
    return parser.parse_args()


def get_avpath(input_dir):
    allav_path = {"audio": [], "video": []}
    for subinput_dir in input_dir:
        if os.path.isfile(subinput_dir):
            file_type = filetype.guess(subinput_dir)
            if file_type:
                if "audio" in filetype.guess(subinput_dir).mime:
                    allav_path["audio"].append(subinput_dir)
                if "video" in filetype.guess(subinput_dir).mime:
                    allav_path["video"].append(subinput_dir)
        elif os.path.isdir(subinput_dir):
            for root, _, files in os.walk(subinput_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_type = filetype.guess(file_path)
                    if file_type:
                        if "audio" in filetype.guess(file_path).mime:
                            allav_path["audio"].append(file_path)
                        if "video" in filetype.guess(file_path).mime:
                            allav_path["video"].append(file_path)

    return allav_path


def extract_audio(
    video_path, output_dir=".", outaudio_format="mp4", outaudio_invideo=False
):
    audio_dir = os.path.join(
        output_dir if outaudio_invideo else tempfile.gettempdir(),
        f"{os.path.basename(os.path.splitext(video_path)[0])}_audio",
    )
    os.makedirs(audio_dir, exist_ok=True)
    audio_path = os.path.join(
        audio_dir,
        f"{os.path.basename(os.path.splitext(video_path)[0])}.{outaudio_format}",
    )

    print(f"Extracting audio from {video_path}...")
    try:
        (
            ffmpeg.input(video_path, threads=0)
            .audio.output(audio_path)
            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
        )
        print(f"Saved audio extracted from video to {os.path.abspath(audio_path)}.")
    except ffmpeg.Error as e:
        raise RuntimeError(f"Failed to extract audio: {e.stderr.decode()}") from e

    return audio_path


def generate_subtitle(
    model,
    allav_path,
    output_dir=".",
    outsubtitle_format="all",
    outaudio_format="wav",
    outvideo_addsubtitle_format="srt",
    outvideo_format="mp4",
    outaudio_invideo=False,
    outvideo_addsubtitle=True,
    outwriter_extra={
        "highlight_words": False,
        "max_line_count": None,
        "max_line_width": None,
        "max_words_per_line": None,
    },
    **args,
):
    # 处理音频文件
    allaudio_path = allav_path["audio"]
    for audio_path in allaudio_path:
        subtitle_dir = os.path.join(
            output_dir, f"{os.path.basename(os.path.splitext(audio_path)[0])}_subtitle"
        )
        os.makedirs(subtitle_dir, exist_ok=True)

        print(f"Generating subtitles for {os.path.basename(audio_path)}...")
        warnings.filterwarnings("ignore")
        result = transcribe(model=model, audio_path=audio_path, **args)
        warnings.filterwarnings("default")

        writer = get_writer(outsubtitle_format, subtitle_dir)
        writer(result, audio_path, **outwriter_extra)

    # 处理视频文件
    allvideo_path = allav_path["video"]
    for video_path in allvideo_path:
        subtitle_dir = os.path.join(
            output_dir, f"{os.path.basename(os.path.splitext(video_path)[0])}_subtitle"
        )
        os.makedirs(subtitle_dir, exist_ok=True)

        print(f"Generating subtitles for {os.path.basename(video_path)}...")
        warnings.filterwarnings("ignore")
        audio_path = extract_audio(
            video_path, output_dir, outaudio_format, outaudio_invideo
        )
        result = transcribe(model=model, audio_path=audio_path, **args)
        warnings.filterwarnings("default")

        writer = get_writer(outsubtitle_format, subtitle_dir)
        writer(result, video_path, **outwriter_extra)

        if outvideo_addsubtitle:
            writer = get_writer(outvideo_addsubtitle_format, subtitle_dir)
            writer(result, video_path, **outwriter_extra)
            subtitle_invideo_path = os.path.join(
                subtitle_dir,
                f"{os.path.basename(os.path.splitext(video_path)[0])}.{outvideo_addsubtitle_format}",
            )
            outvideo_dir = os.path.join(
                output_dir, f"{os.path.basename(os.path.splitext(video_path)[0])}_video"
            )
            os.makedirs(outvideo_dir, exist_ok=True)
            outvideo_path = os.path.join(
                outvideo_dir,
                f"{os.path.basename(os.path.splitext(video_path)[0])}.{outvideo_format}",
            )

            print(f"Adding subtitles to {os.path.basename(video_path)}...")
            video = ffmpeg.input(video_path)
            audio = video.audio
            try:
                video = ffmpeg.filter(
                    video,
                    "subtitles",
                    subtitle_invideo_path,
                    force_style="OutlineColour=&H40000000, BorderStyle=3",
                )
                video = ffmpeg.concat(video, audio, v=1, a=1)
                video.output(outvideo_path).run(
                    capture_stdout=True, capture_stderr=True, overwrite_output=True
                )
                print(f"Saved subtitled video to {os.path.abspath(outvideo_path)}.")
            except ffmpeg.Error as e:
                warnings.warn(
                    f"Adding subtitles to {os.path.basename(video_path)} fail because via python run {e}. maybe subtitles and video formats are incompatible."
                )
                print(
                    f"Next force running a potentially compatible format using ffmpeg on the terminal, and import the generated subtitles for the video yourself if the error continues!!!"
                )
                if outvideo_format == "mp4":
                    os.system(
                        f"ffmpeg -i {video_path} -i {subtitle_invideo_path} -c copy -c:s mov_text {outvideo_path}"
                    )
                else:
                    outvideo_path = f"{os.path.splitext(outvideo_path)[0]}.mkv"
                    os.system(
                        f"ffmpeg -i {video_path} -i {subtitle_invideo_path} -c copy {outvideo_path}"
                    )


def main():
    # 获取参数
    args = get_args().__dict__

    # 获取音频或视频文件的路径
    input_dir: str = args.pop("input_dir")
    assert (not input_dir is None) and all(
        [os.path.exists(path) for path in input_dir]
    ), "You don't give any video or audio path"
    allav_path = get_avpath(input_dir)

    # 创建字幕、音频和视频的输出目录
    output_dir: str = args.pop("output_dir")
    os.makedirs(output_dir, exist_ok=True)

    # 设置保存字幕、音频和视频的参数
    outsubtitle_format: str = args.pop("outsubtitle_format")
    outvideo_addsubtitle_format: str = args.pop("outvideo_addsubtitle_format")
    outaudio_format: str = args.pop("outaudio_format")
    outvideo_format: str = args.pop("outvideo_format")
    outaudio_invideo: str2bool = args.pop("outaudio_invideo")
    outvideo_addsubtitle: str2bool = args.pop("outvideo_addsubtitle")
    outwriter_extra: dict = {
        arg: args.pop(arg)
        for arg in [
            "highlight_words",
            "max_line_count",
            "max_line_width",
            "max_words_per_line",
        ]
    }
    if not args["word_timestamps"]:
        for key, value in outwriter_extra.items():
            assert not value, f"--{key} requires --word_timestamps True"
    if outwriter_extra["max_words_per_line"] and not outwriter_extra["max_line_width"]:
        warnings.warn("--max_words_per_line has no effect with --max_line_width")

    # 导入模型、设置模型参数
    model_name: str = args.pop("model_name")
    assert (
        os.path.isfile(model_name) or model_name in available_models()
    ), 'The model file does not exist please check the input parameter "--model_name"'
    device: str = args.pop("device")
    model_dir: str = args.pop("model_dir")
    model = load_model(model_name, device, model_dir)
    if model_name.endswith(".en") and args["language"] not in {"en", "English"}:
        if args["language"] is not None:
            warnings.warn(
                f"{model_name} is an English model but language receipted {args['language']}; using English instead."
            )
        args["language"] = "en"
    threads: int = args.pop("threads")
    if threads is not None:
        if threads > 0:
            torch.set_num_threads(threads)
    temperature: Union[float, Tuple[float, ...]] = args.pop("temperature")
    if (increment := args.pop("temperature_increment_on_fallback")) is not None:
        args["temperature"] = tuple(np.arange(temperature, 1.0 + 1e-6, increment))
    else:
        args["temperature"] = (temperature,)

    # 提取字幕
    generate_subtitle(
        model,
        allav_path,
        output_dir,
        outsubtitle_format,
        outaudio_format,
        outvideo_addsubtitle_format,
        outvideo_format,
        outaudio_invideo,
        outvideo_addsubtitle,
        outwriter_extra,
        **args,
    )


if __name__ == "__main__":
    main()
