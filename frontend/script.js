class VoiceAgent {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isRecording = false;
        this.websocket = null;
        
        this.recordBtn = document.getElementById('recordBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.status = document.getElementById('status');
        this.conversation = document.getElementById('conversation');
        
        this.initializeEventListeners();
        this.connectWebSocket();
    }
    
    initializeEventListeners() {
        this.recordBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('Record button clicked');
            this.startRecording();
        });
        this.stopBtn.addEventListener('click', (e) => {
            e.preventDefault();
            console.log('Stop button clicked');
            this.stopRecording();
        });
    }
    
    connectWebSocket() {
        // Try localhost first, then WSL IP
        const wsUrls = [
            'ws://localhost:8765',
            'ws://127.0.0.1:8765',
            'ws://172.26.28.187:8765'  // Your WSL IP
        ];
        
        this.connectToWebSocket(wsUrls, 0);
    }
    
    connectToWebSocket(urls, index) {
        if (index >= urls.length) {
            this.updateStatus('Failed to connect to voice agent', 'ready');
            this.recordBtn.disabled = true; // Disable record if no connection
            return;
        }
        
        const url = urls[index];
        console.log(`Trying to connect to: ${url}`);
        
        try {
            this.websocket = new WebSocket(url);
            
            this.websocket.onopen = () => {
                console.log(`WebSocket connected to: ${url}`);
                this.updateStatus('Ready to record', 'ready');
                this.recordBtn.disabled = false; // Enable record button
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateStatus('Disconnected from voice agent', 'ready');
                this.recordBtn.disabled = true; // Disable record if disconnected
            };
            
            this.websocket.onerror = (error) => {
                console.error(`WebSocket error for ${url}:`, error);
                // Try next URL
                setTimeout(() => {
                    this.connectToWebSocket(urls, index + 1);
                }, 1000);
            };
        } catch (error) {
            console.error(`Failed to connect to ${url}:`, error);
            // Try next URL
            setTimeout(() => {
                this.connectToWebSocket(urls, index + 1);
            }, 1000);
        }
    }
    }
    
    async startRecording() {
        console.log('Start recording clicked');
        
        // Check if WebSocket is connected
        if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
            this.updateStatus('Not connected to voice agent', 'ready');
            return;
        }
        
        try {
            console.log('Requesting microphone access...');
            this.updateStatus('Requesting microphone access...', 'processing');
            
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                } 
            });
            
            console.log('Microphone access granted');
            
            this.audioChunks = [];
            
            // Try different MIME types for better compatibility
            let mimeType = 'audio/webm;codecs=opus';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/webm';
                if (!MediaRecorder.isTypeSupported(mimeType)) {
                    mimeType = 'audio/mp4';
                    if (!MediaRecorder.isTypeSupported(mimeType)) {
                        mimeType = '';
                    }
                }
            }
            
            console.log(`Using MIME type: ${mimeType}`);
            
            this.mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : {});
            
            this.mediaRecorder.ondataavailable = (event) => {
                console.log(`Audio chunk received: ${event.data.size} bytes`);
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };
            
            this.mediaRecorder.onstop = () => {
                console.log('Recording stopped');
                this.processRecording();
                stream.getTracks().forEach(track => track.stop());
            };
            
            this.mediaRecorder.onerror = (event) => {
                console.error('MediaRecorder error:', event.error);
                this.updateStatus('Recording error', 'ready');
            };
            
            this.mediaRecorder.start(1000); // Collect data every second
            this.isRecording = true;
            
            this.recordBtn.disabled = true;
            this.recordBtn.classList.add('recording');
            this.recordBtn.textContent = 'Recording...';
            this.stopBtn.disabled = false;
            
            this.updateStatus('Recording... Speak now!', 'recording');
            console.log('Recording started successfully');
            
        } catch (error) {
            console.error('Error starting recording:', error);
            if (error.name === 'NotAllowedError') {
                this.updateStatus('Microphone access denied - please allow microphone access', 'ready');
            } else if (error.name === 'NotFoundError') {
                this.updateStatus('No microphone found', 'ready');
            } else {
                this.updateStatus(`Recording error: ${error.message}`, 'ready');
            }
        }
    }
    
    stopRecording() {
        if (this.mediaRecorder && this.isRecording) {
            this.mediaRecorder.stop();
            this.isRecording = false;
            
            this.recordBtn.disabled = false;
            this.recordBtn.classList.remove('recording');
            this.recordBtn.textContent = 'Start Recording';
            this.stopBtn.disabled = true;
            
            this.updateStatus('Processing...', 'processing');
        }
    }
    
    async processRecording() {
        if (this.audioChunks.length === 0) {
            this.updateStatus('No audio recorded', 'ready');
            return;
        }
        
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
        
        // Convert to base64 for transmission
        const reader = new FileReader();
        reader.onload = () => {
            const base64Audio = reader.result.split(',')[1];
            this.sendAudioToAgent(base64Audio);
        };
        reader.readAsDataURL(audioBlob);
    }
    
    sendAudioToAgent(audioData) {
        if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
            const message = {
                type: 'audio',
                data: audioData,
                timestamp: new Date().toISOString()
            };
            
            this.websocket.send(JSON.stringify(message));
            this.updateStatus('Sent to voice agent...', 'processing');
        } else {
            this.updateStatus('Not connected to voice agent', 'ready');
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'transcription':
                this.addMessage(data.text, 'user');
                this.updateStatus('Processing response...', 'processing');
                break;
                
            case 'response':
                this.addMessage(data.text, 'agent');
                if (data.audio) {
                    this.playAudioResponse(data.audio);
                }
                this.updateStatus('Ready to record', 'ready');
                break;
                
            case 'error':
                console.error('Agent error:', data.message);
                this.updateStatus(`Error: ${data.message}`, 'ready');
                break;
                
            default:
                console.log('Unknown message type:', data.type);
        }
    }
    
    addMessage(text, sender) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}-message`;
        
        const textDiv = document.createElement('div');
        textDiv.textContent = text;
        
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'timestamp';
        timestampDiv.textContent = new Date().toLocaleTimeString();
        
        messageDiv.appendChild(textDiv);
        messageDiv.appendChild(timestampDiv);
        
        this.conversation.appendChild(messageDiv);
        this.conversation.scrollTop = this.conversation.scrollHeight;
    }
    
    playAudioResponse(base64Audio) {
        try {
            const audioBlob = this.base64ToBlob(base64Audio, 'audio/wav');
            const audioUrl = URL.createObjectURL(audioBlob);
            
            const audio = document.createElement('audio');
            audio.controls = true;
            audio.src = audioUrl;
            audio.autoplay = true;
            
            const lastMessage = this.conversation.lastElementChild;
            if (lastMessage && lastMessage.classList.contains('agent-message')) {
                lastMessage.appendChild(audio);
            }
            
            audio.onended = () => {
                URL.revokeObjectURL(audioUrl);
            };
        } catch (error) {
            console.error('Error playing audio response:', error);
        }
    }
    
    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }
    
    updateStatus(message, type) {
        this.status.textContent = message;
        this.status.className = `status ${type}`;
    }
}

// Initialize the voice agent when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new VoiceAgent();
});