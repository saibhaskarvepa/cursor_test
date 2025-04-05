from openai import OpenAI
import os

class OpenAIService:
    def __init__(self, socketio=None):
        self.client = OpenAI()
        self.socketio = socketio

    def transcribe_audio(self, audio_path, target_language="en", request_id=None):
        """
        Transcribes audio file using OpenAI Whisper API and translates to target language
        """
        try:
            # Open audio file
            with open(audio_path, "rb") as audio_file:
                # Transcribe with Whisper
                transcript = self.client.audio.translations.create(
                    model="whisper-1",
                    file=audio_file
                )
                
                # Send progress update
                if request_id and self.socketio:
                    self.socketio.emit('transcription_progress', {
                        'request_id': request_id,
                        'status': 'transcribed',
                        'text': transcript.text
                    })
                
                # Translate if needed
                if target_language != "en":
                    translation = self.client.chat.completions.create(
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
            print(f"Error transcribing audio: {str(e)}")
            return None
        finally:
            # Clean up audio file
            if os.path.exists(audio_path):
                os.remove(audio_path)

# Create a singleton instance
openai_service = OpenAIService() 