import React, { useEffect, useRef, useState } from 'react';
import { Button, View, Text, PermissionsAndroid, Platform } from 'react-native';
import AudioRecord from 'react-native-audio-record';
import io from 'socket.io-client';

export default function App() {
  const socket = useRef(null);
  const [transcript, setTranscript] = useState('');
  const [recording, setRecording] = useState(false);

  useEffect(() => {
    socket.current = io('http://YOUR_SERVER_IP:5000');

    socket.current.on('transcript', text => {
      setTranscript(text);
    });

    AudioRecord.init({
      sampleRate: 16000,
      channels: 1,
      bitsPerSample: 16,
      audioSource: 6,
      wavFile: 'test.wav',
    });

    return () => {
      if (socket.current) socket.current.disconnect();
    };
  }, []);

  async function requestPermissions() {
    if (Platform.OS === 'android') {
      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.RECORD_AUDIO,
      );
      return granted === PermissionsAndroid.RESULTS.GRANTED;
    }
    return true;
  }

  async function startRecording() {
    const hasPermission = await requestPermissions();
    if (!hasPermission) {
      alert('Microphone permission denied');
      return;
    }
    setTranscript('');
    setRecording(true);
    AudioRecord.start();
    AudioRecord.on('data', data => {
      const chunk = Buffer.from(data, 'base64');
      socket.current.emit('audio-stream', chunk);
    });
  }

  async function stopRecording() {
    if (!recording) return;
    await AudioRecord.stop();
    setRecording(false);
  }

  return (
    <View style={{ flex:1, justifyContent:'center', alignItems:'center' }}>
      <Button
        title={recording ? "Stop Recording" : "Start Recording"}
        onPress={recording ? stopRecording : startRecording}
      />
      <Text style={{ marginTop: 20, fontSize: 18 }}>Transcript:</Text>
      <Text style={{ marginTop: 10, fontStyle: 'italic' }}>{transcript}</Text>
    </View>
  );
}
