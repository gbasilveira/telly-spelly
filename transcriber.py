from PyQt6.QtCore import QObject, pyqtSignal, QThread, QTimer
import whisper
import os
import logging
import time
from settings import Settings
logger = logging.getLogger(__name__)


def cuda_is_available():
    """Check whether a usable CUDA GPU is present.

    Imported lazily so the app still runs if torch is replaced by a
    CPU-only build. Returns True only when torch can actually initialize
    a CUDA context.
    """
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception as e:
        logger.warning(f"CUDA availability check failed: {e}")
        return False


def resolve_device(force_gpu=False):
    """Resolve the torch device Whisper should run on.

    Preference order:
      1. cuda when force_gpu is enabled AND a GPU is reachable
      2. cuda when auto-detected (Whisper's historical behavior)
      3. cpu as the final fallback

    Returns a (device, fp16) tuple. fp16 is only safe on CUDA; running
    fp16 on CPU throws, so it is forced to False on cpu.
    """
    cuda_ok = cuda_is_available()
    if force_gpu and not cuda_ok:
        logger.warning(
            "Force GPU is enabled but no CUDA device is available; "
            "falling back to CPU."
        )
    if cuda_ok:
        return "cuda", True
    return "cpu", False


class TranscriptionWorker(QThread):
    finished = pyqtSignal(str, str)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, model, audio_file, language=None, fp16=False):
        super().__init__()
        self.model = model
        self.audio_file = audio_file
        self.language = language
        self.fp16 = fp16

    def run(self):
        try:
            if not os.path.exists(self.audio_file):
                raise FileNotFoundError(f"Audio file not found: {self.audio_file}")

            self.progress.emit("Loading audio file...")

            self.progress.emit("Processing audio with Whisper...")
            result = self.model.transcribe(
                self.audio_file,
                fp16=self.fp16,
                language=self.language
            )
            
            text = result["text"].strip()
            detected_lang = result.get("language", "")
            if not text:
                raise ValueError("No text was transcribed")
                
            self.progress.emit("Transcription completed!")
            logger.info(f"Transcribed text: {text[:100]}...")
            self.finished.emit(text, detected_lang)
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            self.error.emit(f"Transcription failed: {str(e)}")
            self.finished.emit("", "")
        finally:
            try:
                if os.path.exists(self.audio_file):
                    os.remove(self.audio_file)
            except Exception as e:
                logger.error(f"Failed to remove temporary file: {e}")

class WhisperTranscriber(QObject):
    transcription_progress = pyqtSignal(str)
    transcription_finished = pyqtSignal(str, str)
    transcription_error = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.model = None
        self.worker = None
        self.device = "cpu"
        self.fp16 = False
        self._cleanup_timer = QTimer()
        self._cleanup_timer.timeout.connect(self._cleanup_worker)
        self._cleanup_timer.setSingleShot(True)
        self.load_model()

    def load_model(self):
        try:
            settings = Settings()
            model_name = settings.get('model', 'tiny')
            force_gpu = settings.get('force_gpu', False)

            self.device, self.fp16 = resolve_device(force_gpu=force_gpu)
            logger.info(
                f"Loading Whisper model: {model_name} on {self.device.upper()} "
                f"(force_gpu={force_gpu}, fp16={self.fp16})"
            )

            # Redirect whisper's logging to our logger
            import logging as whisper_logging
            whisper_logging.getLogger("whisper").setLevel(logging.WARNING)

            self.model = whisper.load_model(model_name, device=self.device)
            logger.info(
                f"Model loaded successfully on {self.device.upper()}"
            )

        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}")
            raise
        
    def _cleanup_worker(self):
        if self.worker:
            if self.worker.isFinished():
                self.worker.deleteLater()
                self.worker = None
                
    def transcribe_file(self, audio_file):
        if self.worker and self.worker.isRunning():
            logger.warning("Transcription already in progress")
            return
            
        settings = Settings()
        auto_detect = settings.get('auto_detect', True)
        language = None if auto_detect else settings.get('language', 'en')
            
        self.transcription_progress.emit("Starting transcription...")
            
        self.worker = TranscriptionWorker(
            self.model, audio_file, language=language, fp16=self.fp16
        )
        self.worker.finished.connect(self.transcription_finished)
        self.worker.progress.connect(self.transcription_progress)
        self.worker.error.connect(self.transcription_error)
        self.worker.finished.connect(lambda: self._cleanup_timer.start(1000))
        self.worker.start() 
