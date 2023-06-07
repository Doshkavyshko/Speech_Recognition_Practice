import itertools
import speech_recognition as sr
import os
import moviepy.editor as mp

from pydub import AudioSegment


r = sr.Recognizer()
converted_to_wav = "in.wav"


def db_to_float(db, using_amplitude=True):
    db = float(db)
    if using_amplitude:
        return 10 ** (db / 20)
    else:
        return 10 ** (db / 10)


def split_on_silence(audio_segment, min_silence_len=1000, silence_thresh=-16, keep_silence=100,
                     seek_step=1):
    def pairwise(iterable):
        a, b = itertools.tee(iterable)
        next(b, None)
        return zip(a, b)

    if isinstance(keep_silence, bool):
        keep_silence = len(audio_segment) if keep_silence else 0

    output_ranges = [
        [ start - keep_silence, end + keep_silence ]
        for (start,end)
            in detect_nonsilent(audio_segment, min_silence_len, silence_thresh, seek_step)
    ]

    for range_i, range_ii in pairwise(output_ranges):
        last_end = range_i[1]
        next_start = range_ii[0]
        if next_start < last_end:
            range_i[1] = (last_end+next_start)//2
            range_ii[0] = range_i[1]

    return [
        audio_segment[ max(start,0) : min(end,len(audio_segment)) ]
        for start,end in output_ranges
    ]


def detect_silence(audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1):
    seg_len = len(audio_segment)
    if seg_len < min_silence_len:
        return []
    silence_thresh = db_to_float(silence_thresh) * audio_segment.max_possible_amplitude
    silence_starts = []
    last_slice_start = seg_len - min_silence_len
    slice_starts = range(0, last_slice_start + 1, seek_step)
    if last_slice_start % seek_step:
        slice_starts = itertools.chain(slice_starts, [last_slice_start])

    for i in slice_starts:
        audio_slice = audio_segment[i:i + min_silence_len]
        if audio_slice.rms <= silence_thresh:
            silence_starts.append(i)

    if not silence_starts:
        return []

    silent_ranges = []

    prev_i = silence_starts.pop(0)
    current_range_start = prev_i

    for silence_start_i in silence_starts:
        continuous = (silence_start_i == prev_i + seek_step)

        silence_has_gap = silence_start_i > (prev_i + min_silence_len)

        if not continuous and silence_has_gap:
            silent_ranges.append([current_range_start,
                                  prev_i + min_silence_len])
            current_range_start = silence_start_i
        prev_i = silence_start_i

    silent_ranges.append([current_range_start,
                          prev_i + min_silence_len])

    return silent_ranges


def detect_nonsilent(audio_segment, min_silence_len=1000, silence_thresh=-16, seek_step=1):

    silent_ranges = detect_silence(audio_segment, min_silence_len, silence_thresh, seek_step)
    len_seg = len(audio_segment)

    if not silent_ranges:
        return [[0, len_seg]]

    if silent_ranges[0][0] == 0 and silent_ranges[0][1] == len_seg:
        return []

    prev_end_i = 0
    nonsilent_ranges = []
    for start_i, end_i in silent_ranges:
        nonsilent_ranges.append([prev_end_i, start_i])
        prev_end_i = end_i

    if end_i != len_seg:
        nonsilent_ranges.append([prev_end_i, len_seg])

    if nonsilent_ranges[0] == [0, 0]:
        nonsilent_ranges.pop(0)

    return nonsilent_ranges


def transcribe_audio(path, lang):

    with sr.AudioFile(path) as source:
        # r.adjust_for_ambient_noise(source)
        audio_listened = r.record(source)
        # text = r.recognize_vosk(audio_listened, language=lang)
        text = r.recognize_google(audio_listened, language=lang)
    return text


# Функция деления на чанки по тишине между фразами
def splitting_by_silence(path, lang):
    sound = AudioSegment.from_file(path)
    chunks = split_on_silence(sound,
                              min_silence_len=500,
                              silence_thresh=sound.dBFS - 14,
                              keep_silence=200
                              )
    folder = "silence-chunks"
    if not os.path.isdir(folder):
        os.mkdir(folder)
    output_text = ""
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_file = os.path.join(folder, f"chunk{i}.wav")
        audio_chunk.export(chunk_file, format="wav")
        try:
            text = transcribe_audio(chunk_file, lang)# [14:-3]
        except sr.UnknownValueError:
            print("No words to recognize here...")
        else:
            text = f"{text.capitalize()}. "
            print(text)
            output_text += text
    return output_text


# Функция деления на чанки по интервалам времени
def splitting_by_time(path, lang, minutes=1):
    sound = AudioSegment.from_file(path)
    chunk_length_ms = int(1000 * 60 * minutes)
    chunks = [sound[i:i + chunk_length_ms] for i in range(0, len(sound), chunk_length_ms)]
    folder = "interval_chunks"
    if not os.path.isdir(folder):
        os.mkdir(folder)
    output_text = ""
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_file = os.path.join(folder, f"chunk{i}.wav")
        audio_chunk.export(chunk_file, format="wav")
        try:
            text = transcribe_audio(chunk_file, lang)
        except sr.UnknownValueError:
            print("No words to recognize here...")
        else:
            text = f"{text.capitalize()}. "
            print(text)
            output_text += text
    return output_text


# Функция для конвертации mp4 в wav формат
def wav_converter(path):
    input_mp4 = mp.VideoFileClip(path_to_file)
    audio_wav = input_mp4.audio
    audio_wav.write_audiofile("in.wav")


output = open("out.txt", "w")
path_to_file = str(input("Please enter the path to file: "))
lang = str(input("Enter the language: "))
print("Starting convertation process...")
wav_converter(path_to_file)
print("Starting recognition process...")
output.write("\nFull text:" + splitting_by_silence(converted_to_wav, lang))
output.close()
