import gradio as gr
import os
import logging
import wave
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def debug_audio_file(audio_file):
    """Debug function to inspect audio file details"""
    if audio_file is None:
        return "No audio file provided"

    try:
        logger.info(f"Audio file path: {audio_file}")
        logger.info(f"File exists: {os.path.exists(audio_file)}")

        if not os.path.exists(audio_file):
            return "Audio file does not exist"

        file_size = os.path.getsize(audio_file)
        logger.info(f"File size: {file_size} bytes")

        # Try to get file info using ffprobe
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    audio_file,
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.info(f"FFprobe output: {result.stdout}")
            else:
                logger.error(f"FFprobe error: {result.stderr}")
        except FileNotFoundError:
            logger.info("FFprobe not available")

        # Try to read as WAV file
        try:
            with wave.open(audio_file, "rb") as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                duration = frames / sample_rate

                info = f"""
Audio File Information:
- File path: {audio_file}
- File size: {file_size} bytes
- Format: WAV
- Duration: {duration:.2f} seconds
- Sample rate: {sample_rate} Hz
- Channels: {channels}
- Sample width: {sample_width} bytes
- Total frames: {frames}
"""
                logger.info(info)
                return info

        except Exception as e:
            logger.error(f"Error reading WAV file: {e}")

            # Try to read file extension and basic info
            file_ext = os.path.splitext(audio_file)[1].lower()
            info = f"""
Audio File Information:
- File path: {audio_file}
- File size: {file_size} bytes
- Extension: {file_ext}
- Error reading as WAV: {str(e)}
"""
            return info

    except Exception as e:
        error_msg = f"Error analyzing audio file: {str(e)}"
        logger.error(error_msg)
        return error_msg


def simple_test_transcription(audio_file):
    """Simple test that just returns file info"""
    if audio_file is None:
        return "No audio provided", "Please record some audio first."

    file_info = debug_audio_file(audio_file)

    # Simple response
    response = f"Received audio file. Here's the debug info:\n{file_info}"

    return file_info, response


# Create debug interface
with gr.Blocks(title="Audio Debug", theme=gr.themes.Soft()) as app:
    gr.Markdown("# 🔍 Audio Debug Interface")
    gr.Markdown("This will help us debug the audio file format and processing.")

    with gr.Row():
        with gr.Column():
            # Audio input
            audio_input = gr.Audio(label="Record Your Voice", sources=["microphone"])

            # Process button
            process_btn = gr.Button("Analyze Audio", variant="primary")

        with gr.Column():
            # File info output
            file_info_output = gr.Textbox(
                label="Audio File Information",
                placeholder="Audio file details will appear here...",
                lines=10,
            )

            # Response text
            response_text = gr.Textbox(
                label="Response",
                placeholder="Response will appear here...",
                lines=5,
            )

    # Connect the processing function
    process_btn.click(
        fn=simple_test_transcription,
        inputs=[audio_input],
        outputs=[file_info_output, response_text],
    )

if __name__ == "__main__":
    print("🔍 Starting Audio Debug Interface...")
    print("This will help us understand the audio file format.")

    app.launch(server_name="0.0.0.0", server_port=7863, share=False)
