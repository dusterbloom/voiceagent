#!/bin/bash
echo "Starting WhisperLive server..."
cd WhisperLive
python3 run_server.py --port 9091 \
                      --backend faster_whisper
#run_whisper_server.py  --backend faster_whisper --faster_whisper_custom_model_path '$FASTER_WHISPER_MODEL_PATH' --no_single_model