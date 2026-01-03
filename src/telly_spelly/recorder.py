import pyaudio
import wave
from PyQt6.QtCore import QObject, pyqtSignal
import tempfile
import os
import logging
import numpy as np
from .settings import Settings
from scipy import signal

logger = logging.getLogger(__name__)

class AudioRecorder(QObject):
    recording_finished = pyqtSignal(str)  # Emits path to recorded file
    recording_error = pyqtSignal(str)
    volume_updated = pyqtSignal(float)
    
    def __init__(self):
        super().__init__()
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.frames = []
        self.is_recording = False
        self.is_testing = False
        self.test_stream = None
        self.current_device_info = None
        # Keep a reference to self to prevent premature deletion
        self._instance = self
        
    def start_recording(self):
        if self.is_recording:
            return
            
        try:
            self.frames = []
            self.is_recording = True
            
            # Get selected mic index from settings
            settings = Settings()
            mic_index = settings.get('mic_index')
            
            try:
                mic_index = int(mic_index) if mic_index is not None else None
            except (ValueError, TypeError):
                mic_index = None
            
            if mic_index is not None:
                device_info = self.audio.get_device_info_by_index(mic_index)
                logger.info(f"Using selected input device: {device_info['name']}")
            else:
                device_info = self.audio.get_default_input_device_info()
                logger.info(f"Using default input device: {device_info['name']}")
                mic_index = device_info['index']
            
            # Store device info for later use
            self.current_device_info = device_info
            
            # Get supported sample rate from device
            sample_rate = int(device_info['defaultSampleRate'])
            logger.info(f"Using sample rate: {sample_rate}")
            
            self.stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                input=True,
                input_device_index=mic_index,
                frames_per_buffer=1024,
                stream_callback=self._callback
            )
            
            self.stream.start_stream()
            logger.info("Recording started")
            
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self.recording_error.emit(f"Failed to start recording: {e}")
            self.is_recording = False
        
    def _callback(self, in_data, frame_count, time_info, status):
        if status:
            logger.warning(f"Recording status: {status}")
        try:
            if self.is_recording:
                self.frames.append(in_data)
                # Calculate and emit volume level
                try:
                    audio_data = np.frombuffer(in_data, dtype=np.int16)
                    if len(audio_data) > 0:
                        # Calculate RMS with protection against zero/negative values
                        squared = np.abs(audio_data)**2
                        mean_squared = np.mean(squared) if np.any(squared) else 0
                        rms = np.sqrt(mean_squared) if mean_squared > 0 else 0
                        # Normalize to 0-1 range
                        volume = min(1.0, max(0.0, rms / 32768.0))
                    else:
                        volume = 0.0
                    self.volume_updated.emit(volume)
                except Exception as e:
                    logger.warning(f"Error calculating volume: {e}")
                    self.volume_updated.emit(0.0)
                return (in_data, pyaudio.paContinue)
        except RuntimeError:
            # Handle case where object is being deleted
            logger.warning("AudioRecorder object is being cleaned up")
            return (in_data, pyaudio.paComplete)
        return (in_data, pyaudio.paComplete)
        
    def stop_recording(self):
        if not self.is_recording:
            return
            
        logger.info("Stopping recording")
        self.is_recording = False
        
        try:
            # Stop and close the stream first
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            # Check if we have any recorded frames
            if not self.frames:
                logger.error("No audio data recorded")
                self.recording_error.emit("No audio was recorded")
                return
            
            # Process the recording
            self._process_recording()
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            self.recording_error.emit(f"Error stopping recording: {e}")

    def _process_recording(self):
        """Process and save the recording"""
        try:
            temp_file = tempfile.mktemp(suffix='.wav')
            logger.info("Processing recording...")
            self.save_audio(temp_file)
            logger.info(f"Recording processed and saved to: {os.path.abspath(temp_file)}")
            self.recording_finished.emit(temp_file)
        except Exception as e:
            logger.error(f"Failed to process recording: {e}")
            self.recording_error.emit(f"Failed to process recording: {e}")
        
    def save_audio(self, filename):
        """Save recorded audio to a WAV file"""
        try:
            # Convert frames to numpy array
            audio_data = np.frombuffer(b''.join(self.frames), dtype=np.int16)
            
            if self.current_device_info is None:
                raise ValueError("No device info available")
                
            # Get original sample rate from stored device info
            original_rate = int(self.current_device_info['defaultSampleRate'])
            
            # Resample to 16000Hz if needed
            if original_rate != 16000:
                # Calculate resampling ratio
                ratio = 16000 / original_rate
                output_length = int(len(audio_data) * ratio)
                
                # Resample audio
                audio_data = signal.resample(audio_data, output_length)
            
            # Save to WAV file
            wf = wave.open(filename, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.audio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(16000)  # Always save at 16000Hz for Whisper
            wf.writeframes(audio_data.astype(np.int16).tobytes())
            wf.close()
            
            # Log the saved file location
            logger.info(f"Recording saved to: {os.path.abspath(filename)}")
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {e}")
            raise
        
    def start_mic_test(self, device_index):
        """Start microphone test"""
        if self.is_testing or self.is_recording:
            return
            
        try:
            self.test_stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                input=True,
                input_device_index=device_index,
                frames_per_buffer=1024,
                stream_callback=self._test_callback
            )
            
            self.test_stream.start_stream()
            self.is_testing = True
            logger.info(f"Started mic test on device {device_index}")
            
        except Exception as e:
            logger.error(f"Failed to start mic test: {e}")
            raise
            
    def stop_mic_test(self):
        """Stop microphone test"""
        if self.test_stream:
            self.test_stream.stop_stream()
            self.test_stream.close()
            self.test_stream = None
        self.is_testing = False
        
    def _test_callback(self, in_data, frame_count, time_info, status):
        """Callback for mic test"""
        if status:
            logger.warning(f"Test callback status: {status}")
        return (in_data, pyaudio.paContinue)
        
    def get_current_audio_level(self):
        """Get current audio level for meter"""
        if not self.test_stream or not self.is_testing:
            return 0
            
        try:
            data = self.test_stream.read(1024, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.float32)
            return np.sqrt(np.mean(np.square(audio_data)))
        except Exception as e:
            logger.error(f"Error getting audio level: {e}")
            return 0

    def cleanup(self):
        """Cleanup resources"""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        if self.test_stream:
            self.test_stream.stop_stream()
            self.test_stream.close()
            self.test_stream = None
        if self.audio:
            self.audio.terminate()
            self.audio = None
        self._instance = None 