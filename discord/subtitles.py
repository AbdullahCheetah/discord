import re
import moviepy.editor as mp
from whisper_timestamped import load_model, transcribe_timestamped
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
WHISPER_MODEL = None

def extract_audio_from_video(video_file_path, filename):
    clip = mp.VideoFileClip(video_file_path)
    clip.audio.write_audiofile(f"audio/{filename}.mp3")
    return f"audio/{filename}.mp3"


def getSpeechBlocks(whispered, silence_time=2):
    text_blocks, (st, et, txt) = [], (0,0,"")
    for i, seg in enumerate(whispered['segments']):
        if seg['start'] - et > silence_time:
            if txt: text_blocks.append([[st, et], txt])
            (st, et, txt) = (seg['start'], seg['end'], seg['text'])
        else:
            et, txt = seg['end'], txt + seg['text']
    if txt: text_blocks.append([[st, et], txt])
    return text_blocks

def cleanWord(word):
    return re.sub(r'[^\w\s\-_"\'\']', '', word)

def interpolateTimeFromDict(word_position, d):
    for key, value in d.items():
        if key[0] <= word_position <= key[1]:
            return value
    return None

def getTimestampMapping(whisper_analysis):
    index = 0
    locationToTimestamp = {}
    for segment in whisper_analysis['segments']:
        for word in segment['words']:
            newIndex = index + len(word['text'])+1
            locationToTimestamp[(index, newIndex)] = word['end']
            index = newIndex
    return locationToTimestamp

def splitWordsBySize(words, maxCaptionSize):
    halfCaptionSize = maxCaptionSize / 2
    captions = []
    while words:
        caption = words[0]
        words = words[1:]
        while words and len(caption + ' ' + words[0]) <= maxCaptionSize:
            caption += ' ' + words[0]
            words = words[1:]
            if len(caption) >= halfCaptionSize and words:
                break
        captions.append(caption)
    return captions

def getCaptionsWithTime(whisper_analysis, maxCaptionSize=15, considerPunctuation=False, min_duration=0.5):
    wordLocationToTime = getTimestampMapping(whisper_analysis)
    position = 0
    start_time = 0
    CaptionsPairs = []
    text = whisper_analysis['text']

    if considerPunctuation:
        sentences = re.split(r'(?<=[.!?]) +', text)
        words = [word for sentence in sentences for word in splitWordsBySize(sentence.split(), maxCaptionSize)]
    else:
        words = text.split()
        words = [cleanWord(word) for word in splitWordsBySize(words, maxCaptionSize)]

    for word in words:
        position += len(word) + 1
        end_time = interpolateTimeFromDict(position, wordLocationToTime)
        if end_time and word:
            # Ensure there is a minimum duration for each caption
            end_time = max(end_time, start_time + min_duration)
            CaptionsPairs.append(((start_time, end_time), word))
            start_time = end_time

    return CaptionsPairs


def audioToText(filename, model_size="base"):
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        WHISPER_MODEL = load_model(model_size)
    gen = transcribe_timestamped(WHISPER_MODEL, filename, verbose=False, fp16=False)
    return gen


def get_subtitles(video_file_path):
    filename = video_file_path.split('/')[-1].split('.')[0]
    audio_file_path = extract_audio_from_video(video_file_path, filename)
    whisper_analysis = audioToText(audio_file_path)
    captions_with_time = getCaptionsWithTime(whisper_analysis)
    print(captions_with_time)
    final_clip= VideoFileClip(video_file_path)

    caption_config = {
        "fontsize": 35,
        "font": "Arial-Bold",
        "color": "green",
        "size": (200, None),
        "position": "center"
    }

    caption_clips = []
    for (start_time, end_time), caption in captions_with_time:
        txt_clip = TextClip(caption, fontsize=caption_config['fontsize'], color=caption_config['color'],
                            stroke_width=caption_config['stroke_width'], stroke_color=caption_config['stroke_color'],
                            font=caption_config['font'], size=caption_config['size'])
        duration=end_time-start_time
        txt_clip = txt_clip.set_position(caption_config['position']).set_duration(end_time - start_time).set_start(start_time)
        caption_clips.append(txt_clip)

    final_video = CompositeVideoClip([final_clip] + caption_clips)
    final_video.write_videofile(f"merged_video_with_captions_{filename}.mp4", codec='libx264', audio_codec='aac', threads=24)
    return f"merged_video_with_captions_{filename}.mp4"