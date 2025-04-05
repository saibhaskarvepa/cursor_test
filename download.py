import yt_dlp
from moviepy.editor import VideoFileClip 
import os

def download_youtube_video(url, output_path="downloads"):
    """
    Downloads a YouTube video and extracts the audio
    """
    try:
        # Create downloads directory if it doesn't exist
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4'
        }
        
        # Download video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info)
        
        # Extract audio from video
        video_clip = VideoFileClip(video_path)
        audio_path = os.path.join(output_path, "audio.mp3")
        video_clip.audio.write_audiofile(audio_path)
        
        # Clean up video file
        video_clip.close()
        os.remove(video_path)
        
        return audio_path
        
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None 