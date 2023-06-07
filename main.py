import speech_recognition as sr
import os
from pydub import AudioSegment
from pydub.silence import split_on_silence
import moviepy.editor as mp

r = sr.Recognizer()


def transcribe_audio(path, lang):
    with sr.AudioFile(path) as source:
        # r.adjust_for_ambient_noise(source)
        audio_listened = r.record(source)
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
    folder = "audio-chunks"
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
output.write("\nFull text:" + splitting_by_time("in.wav", lang, minutes=1 / 6))
