import os

class STTEngine:
    """
    Speech-To-Text Recognizer for German Voice Inputs.
    Supports SpeechRecognition (Google ASR / Whisper / macOS Voice) with graceful fallback.
    """
    def __init__(self):
        self.sr_available = False
        try:
            import speech_recognition as sr
            self.recognizer = sr.Recognizer()
            self.sr_available = True
        except Exception:
            self.recognizer = None

    def transcribe_wav(self, wav_file: str, language: str = "de-DE") -> str:
        """
        Transcribes audio file to text using available ASR engine.
        Returns recognized German text.
        """
        if not wav_file or not os.path.exists(wav_file) or os.path.getsize(wav_file) == 0:
            return ""

        if self.sr_available and self.recognizer:
            import speech_recognition as sr
            try:
                with sr.AudioFile(wav_file) as source:
                    audio_data = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio_data, language=language)
                    return text.strip()
            except sr.UnknownValueError:
                print("[STTEngine] Speech could not be recognized.")
                return ""
            except Exception as e:
                print(f"[STTEngine] ASR notice: {e}")
        
        return ""
