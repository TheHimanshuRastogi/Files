import os
import time
import random
import yt_dlp
import gspread
import requests
from moviepy.editor import (
    concatenate_videoclips,
    CompositeVideoClip,
    AudioFileClip,
    VideoFileClip,
    ImageClip,
    TextClip
)


VIDEOS = [
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/1wgdrm.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/4z1wwg.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/5d9k0p.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/akfqcp.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/bo8056.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/ittrcs.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/n4cfvb.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/qy6i2q.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/rnrh34.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/wnxu7e.mp4',
    'https://github.com/TheHimanshuRastogi/Files/raw/main/1280x720/yeshu3.mp4'
    ] 


USERS = [1250003833]
WORKSHEET_NAME = 'music'
BOT_TOKEN = '5976977139:AAGoCproKvJDCmgbSwbvJQ3X0YjsJpqZ9vY'
SPREADSHEET_URL = '1GKI0AK2bLfB409I8TUas6CJZwbVGkbbjqE0R7rgs7jk'


def get_transcription() -> dict|bool:

    client = gspread.service_account(filename='credentials.json')
    music_sheet = client.open_by_key(SPREADSHEET_URL).worksheet(WORKSHEET_NAME)

    all_transcriptions = music_sheet.get_all_records()
    pending_transcription = {}

    for transcription in all_transcriptions:
        if transcription['is_video'] != "TRUE" and "pending":
            pending_transcription = transcription
            break

    if pending_transcription:
        transcription = []
        for lyric in pending_transcription['transcription'].split('|'):
            Dict = {}
            time, text = lyric.split(':')
            start, end = time.split('-')
            Dict['start'] = float(start)
            Dict['end'] = float(end)
            Dict['text'] = str(text)
            transcription.append(Dict)
        pending_transcription['transcription'] = transcription
        return pending_transcription
    else:
        return False


def youtube(url: str) -> str:
    ydl_opts = {
        'format': 'bestaudio/best',  # Choose the best audio quality available
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',  # Extract audio using ffmpeg
            'preferredcodec': 'mp3',  # Convert audio to mp3 format
            'preferredquality': '192',  # Set the audio quality to 192kbps
        }],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        audio_path = ydl.prepare_filename(info_dict)
    
    return os.path.abspath(audio_path.replace('webm', 'mp3'))


def create_video(json_data: dict, music_path: str) -> str:

    def download_video(url: str) -> str:
        response = requests.get(url)
        download_path = os.path.join(os.getcwd(), os.path.basename(url)) 
        with open(download_path, "wb") as f:
            f.write(response.content)
        return download_path
    
    text_clips = []
    duration = json_data['end']-json_data['start']
    for item in json_data['transcription']:
        text = item['text']
        start, end = item['start'], item['end']
        
        text_clip = TextClip( # Creating TextClip from text given
            txt=text, 
            size=(850, 1800), # Text remain in frame
            method='caption', # Text Wrapping
            fontsize=60,
            color='white',
            font="UniSansHeavyCAPS",
            stroke_width=3,
            stroke_color='Black'
        )
        
        text_clip = text_clip.set_start(start) # Start time of Text
        text_clip = text_clip.set_position('center') 
        text_clip = text_clip.set_duration(end-start) # Text Duration
        text_clips.append(text_clip)

    text_final_clip = CompositeVideoClip(text_clips) # Composite all text clips
    text_final_clip = text_final_clip.set_position("center") 

    bg = download_video(random.choice(VIDEOS))
    video = VideoFileClip(bg)
    width, height = video.size

    # Upscale video
    if 700 < height < 800: # 720p
        video = video.resize(width=width*2.8, height=height*2.8) 
    elif 1000 < height < 1100: # 1080p
        video = video.resize(width=width*1.8, height=height*1.8) 
    elif 1400 < height < 1500: # 1440p
        video = video.resize(width=width*1.4, height=height*1.4) 

    width, height = video.size # New size of video
    video = video.crop(x1=(width/2)-540, y1=(height/2)-960, x2=(width/2)+540, y2=(height/2)+960)  # Crop video

    if video.duration < duration: # Concatenate videos if duration of background video is less than duaration of sum of texts
        video = concatenate_videoclips([video for _ in range(int(duration//video.duration)+1)]) 
    
    video = video.subclip(0, duration) # Trim video
    video = video.set_audio(None) # Turn off default music if any

    video_with_text = CompositeVideoClip([video, text_final_clip]) # Place texts over the video
    music = AudioFileClip(music_path)
    music = music.subclip(json_data['start'], json_data['end']) # Trim Music
    video_with_text = video_with_text.set_audio(music) # Set music

    output_file = music_path.replace('mp3', 'mp4')
    video_with_text.write_videofile( # Export video
        output_file,
        fps = 30,
        codec = 'libx264',
        audio_codec = 'aac',
        bitrate = '5M',
        threads = 4,
        preset = 'medium'
    )

    # Relesase all clips
    video.close()
    music.close()
    text_clip.close()
    video_with_text.close()
    text_final_clip.close()
    
    os.remove(music_path) # Delete music file
    os.remove(bg) # Delete background video

    return output_file, bg


def update_value(video_url: str, value: str) -> True:
    client = gspread.service_account(filename='credentials.json')
    music_sheet = client.open_by_key(SPREADSHEET_URL).worksheet(WORKSHEET_NAME)
    cell = music_sheet.find(video_url)
    music_sheet.update_cell(cell.row, cell.col+7, value)
    return True


def telegram(video_path: str, caption: str) -> True:
    api_url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendDocument'
    for user in USERS:
        with open(video_path, 'rb') as video_file:
            response = requests.post(api_url, data={'chat_id': user, 'caption': caption}, files={'document': video_file})
    if response.status_code == 200:
        return True
    else:
        return response.status_code


def CreateVideo() -> str:

    def format_time(seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = (seconds % 3600) % 60

        time_str = ""
        if hours > 0:
            time_str += f"{hours} hours "
        if minutes > 0:
            time_str += f"{minutes} minutes "
        time_str += f"{seconds} seconds"

        return time_str

    start = time.time()

    print("\033[92m" + "Getting data from Google Sheets..." + "\033[0m")
    data = get_transcription() # Get data from Google Sheets
    if not data:
        print("There are no transcription to create videos in Google Sheets, add some transcriptions to create videos.")
        return 
    
    update_value(
        video_url=data['video_url'],
        value='pending'
    )

    print("\033[92m" + "Downloading music..." + "\033[0m")
    music_path = youtube( # Download the music using yt_dlp
        url=data['video_url']  
    )

    print("\033[92m" + "Creating Video..." + "\033[0m")
    video_path, bg = create_video(
        json_data=data,
        music_path=music_path
    )

    update_value(
        video_url=data['video_url'],
        value='TRUE'
    )

    end = time.time()
    total_time = format_time(round(end-start))

    print("\033[92m" + "Uploading to Telegram..." + "\033[0m")
    upload_status = telegram(
        video_path=video_path,
        caption=f"File Name: {video_path.split('/')[-1]}\nTime Taken: {total_time}\nVideo used: {bg.split('/')[-1]}"
    )

    return upload_status

if __name__ == '__main__':
    CreateVideo()
