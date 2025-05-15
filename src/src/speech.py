# import azure.cognitiveservices.speech as speechsdk
# import streamlit as st 
# import os
# from dotenv import load_dotenv
# import pathlib

# # Load environment variables
# load_dotenv()


# def load_css(file_name):  
#     with open(file_name) as f:  
#         st.html(f"<style>{f.read()}</style>")

# css_path = pathlib.Path("style.css")
# load_css(css_path)
# lang_code = "en-US"  # Use correct language code for Azure Speech
# speech_key = os.getenv('SPEECH_KEY')
# service_region = os.getenv('SERVICE_REGION')


# def transcribe_real_time_audio(lang_code):
#     try:
#         # Set up the speech configuration
#         speech_config = speechsdk.SpeechConfig(
#             subscription=os.getenv('SPEECH_KEY'),
#             region=os.getenv('SERVICE_REGION')
#         )
#         speech_config.speech_recognition_language = lang_code
#         audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
#         speech_recognizer = speechsdk.SpeechRecognizer(
#             speech_config=speech_config, 
#             audio_config=audio_config
#         )

#         with st.spinner("Listening 🔴..."):
#             result = speech_recognizer.recognize_once_async().get()

#             if result.reason == speechsdk.ResultReason.RecognizedSpeech:
#                 st.session_state['transcribed_text'] = result.text
#                 st.session_state['transcription_success'] = True
#             elif result.reason == speechsdk.ResultReason.NoMatch:
#                 st.error("No speech could be recognized.")
#             elif result.reason == speechsdk.ResultReason.Canceled:
#                 cancellation_details = result.cancellation_details
#                 st.error(f"Canceled: {cancellation_details.reason}")
#                 if cancellation_details.reason == speechsdk.CancellationReason.Error:
#                     st.error(f"Error details: {cancellation_details.error_details}")

#     except Exception as e:
#         st.error(f"An error occurred: {e}")

#AUDIO 
import pyaudio
import wave
import os
import time
import tempfile
import azure.cognitiveservices.speech as speechsdk
import audioop

# Azure Credentials
AZURE_SPEECH_KEY = os.getenv("SPEECH_KEY")
AZURE_REGION = os.getenv("SERVICE_REGION")

# Recording Settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_THRESHOLD = 1500  # Adjust based on background noise level
SILENCE_DURATION = 2  # Stop recording after 2 seconds of silence

def record_audio_with_silence_detection():
    """Records audio and stops when silence is detected for 2 seconds."""
    audio = pyaudio.PyAudio()
    stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("🎤 Recording started... Speak now!")

    frames = []
    silence_start = None  # Track when silence starts

    while True:
        data = stream.read(CHUNK)
        frames.append(data)

        # Detect silence using audioop
        rms = audioop.rms(data, 2)  # Get volume level
        if rms < SILENCE_THRESHOLD:
            if silence_start is None:
                silence_start = time.time()  # Mark when silence started
            elif time.time() - silence_start > SILENCE_DURATION:
                print("🔇 Silence detected! Stopping recording...")
                break  # Stop if silence lasts more than 2 seconds
        else:
            silence_start = None  # Reset silence timer if voice is detected

    # Stop and close stream
    stream.stop_stream()
    stream.close()
    audio.terminate()

    # Save audio to a temp file
    temp_audio_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    with wave.open(temp_audio_file.name, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))

    print(f"✅ Recording complete! Saved as: {temp_audio_file.name}")
    return temp_audio_file.name  # Return temp file path

def transcribe_audio_file(audio_path):
    """Sends audio file to Azure Speech for transcription."""
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_SPEECH_KEY, region=AZURE_REGION)
    audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
    speech_recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

    print("🎧 Transcribing audio...")
    result = speech_recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"📝 Transcription: {result.text}")
        return result.text
    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("❌ No speech recognized.")
        return "No speech recognized."
    elif result.reason == speechsdk.ResultReason.Canceled:
        print(f"⚠️ Error: {result.cancellation_details.reason}")
        return "Error in transcription."

    return ""


