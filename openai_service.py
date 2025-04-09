import openai
import os
from dotenv import load_dotenv

load_dotenv()

class OpenAIService:
    def __init__(self, socketio=None):
        self.socketio = socketio
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")

    def transcribe_audio(self, audio_path, target_language="en", request_id=None):
        """
        Transcribes audio file using OpenAI Whisper API and translates to target language
        """
        try:
            # Open audio file
            with open(audio_path, "rb") as audio_file:
                # Transcribe with Whisper
                transcript = openai.Audio.transcribe(
                    "whisper-1",
                    audio_file,
                    language=target_language
                )
                
                # Send progress update
                if request_id and self.socketio:
                    self.socketio.emit('transcription_progress', {
                        'request_id': request_id,
                        'status': 'completed',
                        'transcript': transcript.text
                    })
                
                # Translate if needed
                if target_language != "en":
                    translation = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[
                            {"role": "system", "content": f"You are a translator. Translate the following text to {target_language}:"},
                            {"role": "user", "content": transcript.text}
                        ]
                    )
                    result = translation.choices[0].message.content
                    
                    # Send translation update
                    if request_id and self.socketio:
                        self.socketio.emit('translation_progress', {
                            'request_id': request_id,
                            'status': 'translated',
                            'text': result
                        })
                    
                    return result
                    
                return transcript.text
                
        except Exception as e:
            if self.socketio and request_id:
                self.socketio.emit('transcription_progress', {
                    'request_id': request_id,
                    'status': 'error',
                    'error': str(e)
                })
            raise e
        finally:
            # Clean up audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)

# Initialize the service
openai_service = OpenAIService() 