import yt_dlp
import os

def download_youtube_video(url, output_path="downloads"):
    """
    Downloads a YouTube video and extracts the audio using yt-dlp
    """
    try:
        # Create downloads directory if it doesn't exist
        if not os.path.exists(output_path):
            os.makedirs(output_path)
            
        # Configure yt-dlp options for audio extraction
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, 'audio.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        # Download and extract audio
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            audio_path = ydl.prepare_filename(info)
            # Change extension to .mp3 since we specified mp3 in postprocessors
            audio_path = os.path.splitext(audio_path)[0] + '.mp3'
        
        return audio_path
        
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None 