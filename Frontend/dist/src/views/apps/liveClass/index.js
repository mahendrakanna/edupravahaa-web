// LiveClassPage.js
import { useState, useRef, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import './indec.css';

import VideocamIcon from '@mui/icons-material/Videocam';
import VideocamOffIcon from '@mui/icons-material/VideocamOff';
import MicIcon from '@mui/icons-material/Mic';
import MicOffIcon from '@mui/icons-material/MicOff';
import ScreenShareIcon from '@mui/icons-material/ScreenShare';
import StopScreenShareIcon from '@mui/icons-material/StopScreenShare';
import ChatBubbleOutlineIcon from '@mui/icons-material/ChatBubbleOutline';
import CallEndIcon from '@mui/icons-material/CallEnd';
import PersonIcon from '@mui/icons-material/Person';
import EmojiEmotionsIcon from '@mui/icons-material/EmojiEmotions';
import PanToolAltIcon from '@mui/icons-material/PanToolAlt';
import GroupsIcon from '@mui/icons-material/Groups';
import { useSelector } from 'react-redux';

const LiveClassPage = () => {
  const { courseId } = useParams();
  const { user } = useSelector(state => state.auth);
  const { token } = useSelector(state => state.auth);
  const isTeacher = user?.role === 'teacher';

  const ws = useRef(null);

  // States
  const [joined, setJoined] = useState(false);
  const [localStream, setLocalStream] = useState(null);
  const [screenStream, setScreenStream] = useState(null);
  const [remoteStreams, setRemoteStreams] = useState([]); // ✅ multiple streams
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [audioEnabled, setAudioEnabled] = useState(true);
  const [screenSharing, setScreenSharing] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [meetingTime, setMeetingTime] = useState('00:00:00');
  const [participants, setParticipants] = useState([{ id: user?.id, name: 'You', handRaised: false }]);
  const [showEmoji, setShowEmoji] = useState(false);
  const [emoji, setEmoji] = useState('');
  const [handRaised, setHandRaised] = useState(false);

  // Refs
  const localVideoRef = useRef();
  const screenShareVideoRef = useRef();
  const peerConnection = useRef();
  const meetingTimer = useRef();

  // Preview before joining
  useEffect(() => {
    if (!joined) {
      initializePreview();
    }
    return () => {
      if (localStream) localStream.getTracks().forEach(track => track.stop());
      if (screenStream) screenStream.getTracks().forEach(track => track.stop());
      if (meetingTimer.current) clearInterval(meetingTimer.current);
    };
  }, [joined]);

  const initializePreview = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: isTeacher
      });
      setLocalStream(stream);
      if (localVideoRef.current) localVideoRef.current.srcObject = stream;

      if (!isTeacher) {
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
          audioTrack.enabled = false;
          setAudioEnabled(false);
        }
      }
    } catch (error) {
      console.error('Error accessing media devices:', error);
    }
  };

  const initializeMeetingMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: isTeacher
      });
      setLocalStream(stream);
      if (localVideoRef.current) localVideoRef.current.srcObject = stream;
      startMeetingTimer();
      initializeWebRTC(stream);
    } catch (error) {
      console.error('Error accessing media devices:', error);
    }
  };

  // ---------------- WebSocket Setup ----------------
  const connectWebSocket = () => {
    ws.current = new WebSocket(`ws://192.168.0.17:8000/ws/class/${14}/?token=Bearer%20${token}`);
    // ws.current = new WebSocket(`ws://localhost:8000/ws/class/${3}/?token=Bearer%20${token}`);
15

    ws.current.onopen = () => {
      console.log("✅ WebSocket connected");
      ws.current.send(JSON.stringify({ type: "join", userId: user?.id, user: user?.name || "Guest" }));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log("📩 WS Message:", data);

      switch (data.type) {
        case "offer":
          handleOffer(data.offer);
          break;
        case "answer":
          handleAnswer(data.answer);
          break;
        case "candidate":
          handleCandidate(data.candidate);
          break;
        case "chat":
          setMessages(prev => [...prev, { sender: data.sender, message: data.message, timestamp: new Date().toLocaleTimeString() }]);
          break;
        case "participants":
          setParticipants(data.participants);
          break;
        case "raise-hand": // ✅ student raised hand
          if (isTeacher) {
            setParticipants(prev =>
              prev.map(p => p.id === data.userId ? { ...p, handRaised: true } : p)
            );
          }
          break;
        case "unmute": // ✅ teacher approved unmute
          if (!isTeacher && data.userId === user.id) {
            const audioTrack = localStream.getAudioTracks()[0];
            if (audioTrack) {
              audioTrack.enabled = true;
              setAudioEnabled(true);
            }
          }
          break;
        default:
          break;
      }
    };

    ws.current.onclose = () => console.log("❌ WebSocket disconnected");
  };

  // ---------------- WebRTC Signaling ----------------
  const initializeWebRTC = (stream) => {
    const configuration = { iceServers: [{ urls: "stun:stun.l.google.com:19302" }] };
    peerConnection.current = new RTCPeerConnection(configuration);

    stream.getTracks().forEach(track => peerConnection.current.addTrack(track, stream));

    peerConnection.current.ontrack = (event) => {
      const newStream = event.streams[0];
      setRemoteStreams(prev => {
        if (!prev.find(s => s.id === newStream.id)) {
          return [...prev, newStream];
        }
        return prev;
      });
    };

    peerConnection.current.onicecandidate = (event) => {
      if (event.candidate) {
        ws.current?.send(JSON.stringify({ type: "candidate", candidate: event.candidate, sender: user?.id }));
      }
    };

    if (isTeacher) {
      peerConnection.current.createOffer()
        .then(offer => peerConnection.current.setLocalDescription(offer))
        .then(() => {
          ws.current?.send(JSON.stringify({ type: "offer", offer: peerConnection.current.localDescription, sender: user?.id }));
        });
    }
  };

  const handleOffer = async (offer) => {
    if (!peerConnection.current) initializeWebRTC(localStream);

    await peerConnection.current.setRemoteDescription(new RTCSessionDescription(offer));
    const answer = await peerConnection.current.createAnswer();
    await peerConnection.current.setLocalDescription(answer);

    ws.current?.send(JSON.stringify({ type: "answer", answer, sender: user?.id }));
  };

  const handleAnswer = async (answer) => {
    await peerConnection.current.setRemoteDescription(new RTCSessionDescription(answer));
  };

  const handleCandidate = async (candidate) => {
    try {
      await peerConnection.current.addIceCandidate(new RTCIceCandidate(candidate));
    } catch (err) {
      console.error("Error adding ICE candidate", err);
    }
  };

  // ---------------- Meeting Controls ----------------
  const startMeetingTimer = () => {
    let startTime = Date.now();
    meetingTimer.current = setInterval(() => {
      const elapsedTime = Date.now() - startTime;
      const hours = Math.floor(elapsedTime / 3600000).toString().padStart(2, '0');
      const minutes = Math.floor((elapsedTime % 3600000) / 60000).toString().padStart(2, '0');
      const seconds = Math.floor((elapsedTime % 60000) / 1000).toString().padStart(2, '0');
      setMeetingTime(`${hours}:${minutes}:${seconds}`);
    }, 1000);
  };

  const toggleVideo = () => {
    if (localStream) {
      const videoTrack = localStream.getVideoTracks()[0];
      if (videoTrack) {
        videoTrack.enabled = !videoTrack.enabled;
        setVideoEnabled(videoTrack.enabled);
      }
    }
  };

  const toggleAudio = () => {
    if (localStream) {
      const audioTrack = localStream.getAudioTracks()[0];
      if (audioTrack) {
        audioTrack.enabled = !audioTrack.enabled;
        setAudioEnabled(audioTrack.enabled);
      }
    }
  };

  const toggleScreenShare = async () => {
    if (isTeacher) {
      if (!screenSharing) {
        try {
          const screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
          setScreenStream(screenStream);
          if (screenShareVideoRef.current) screenShareVideoRef.current.srcObject = screenStream;

          const videoTrack = screenStream.getVideoTracks()[0];
          const sender = peerConnection.current.getSenders().find(s => s.track?.kind === 'video');
          if (sender) sender.replaceTrack(videoTrack);

          setScreenSharing(true);
          videoTrack.onended = () => toggleScreenShare();
        } catch (error) {
          console.error("Error screen sharing", error);
        }
      } else {
        try {
          const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: isTeacher });
          const videoTrack = stream.getVideoTracks()[0];
          const sender = peerConnection.current.getSenders().find(s => s.track?.kind === 'video');
          if (sender) sender.replaceTrack(videoTrack);

          if (screenStream) screenStream.getTracks().forEach(track => track.stop());
          setScreenStream(null);
          if (localVideoRef.current) localVideoRef.current.srcObject = stream;
          setLocalStream(stream);
          setScreenSharing(false);
        } catch (error) {
          console.error("Error switching back to camera", error);
        }
      }
    }
  };

  // ---------------- Chat ----------------
  const sendMessage = () => {
    if (messageInput.trim()) {
      const newMessage = {
        id: Date.now(),
        message: messageInput,
        sender: user?.name || 'You',
        timestamp: new Date().toLocaleTimeString()
      };
      setMessages([...messages, newMessage]);

      ws.current?.send(
        JSON.stringify({ type: "chat", message: messageInput, sender: user?.name })
      );

      setMessageInput('');
    }
  };

  // ---------------- Meeting Join/Leave ----------------
  const joinMeeting = () => {
    setJoined(true);
    connectWebSocket();
    initializeMeetingMedia();
  };

  const leaveCall = () => {
    if (localStream) localStream.getTracks().forEach(track => track.stop());
    if (screenStream) screenStream.getTracks().forEach(track => track.stop());
    if (meetingTimer.current) clearInterval(meetingTimer.current);
    if (ws.current) { ws.current.close(); ws.current = null; }
    if (peerConnection.current) { peerConnection.current.close(); peerConnection.current = null; }
    setJoined(false);
    setScreenSharing(false);
    setHandRaised(false);
    setShowEmoji(false);
    setEmoji('');
  };

  const handleRaiseHand = () => {
    ws.current?.send(JSON.stringify({ type: "raise-hand", userId: user.id }));
    setHandRaised(true);
  };

  const unmuteStudent = (studentId) => {
    ws.current?.send(JSON.stringify({ type: "unmute", userId: studentId }));
  };

  const handleEmoji = (emojiVal) => {
    setShowEmoji(true);
    setEmoji(emojiVal);
    setTimeout(() => { setShowEmoji(false); setEmoji(''); }, 2000);
  };

  // ---------------- UI ----------------
  if (!joined) {
    return (
      <div className="prejoin-container">
        <div className="prejoin-header">
          <div className="google-meet-logo">Live Meet</div>
          <div className="meeting-info">
            <h2>{user?.name}</h2>
            <p>Do you want people to see and hear you in the meeting?</p>
          </div>
        </div>
        <div className="video-preview">
          <video ref={localVideoRef} autoPlay muted className="preview-video"></video>
        </div>
        <div className="media-controls-prejoin">
          <button onClick={toggleVideo} className="control-button-prejoin">
            {videoEnabled ? <VideocamIcon /> : <VideocamOffIcon />}
            <span>{videoEnabled ? 'Camera on' : 'Camera off'}</span>
          </button>
          {isTeacher && (
            <button onClick={toggleAudio} className="control-button-prejoin">
              {audioEnabled ? <MicIcon /> : <MicOffIcon />}
              <span>{audioEnabled ? 'Microphone on' : 'Microphone off'}</span>
            </button>
          )}
        </div>
        <div className="join-actions">
          <button onClick={joinMeeting} className="join-button">Join now</button>
          <div className="meeting-id">Meeting ID: {courseId}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="meeting-container">
      {/* Header */}
      <div className="meeting-header">
        <div className="meeting-info-header">
          <span className="meeting-time">{meetingTime}</span>
          <span className="meeting-id-header">Meeting ID: {courseId}</span>
          <span className="user-role">({user?.role})</span>
        </div>
        <div className="meeting-title">{user?.name} (You, {screenSharing ? 'presenting' : 'joined'})</div>
      </div>

      {/* Video Area */}
      <div className="video-container">
        <div className="remote-video">
          {screenSharing ? (
            <video ref={screenShareVideoRef} autoPlay className="main-video"></video>
          ) : remoteStreams.length > 0 ? (
            <video
              ref={el => { if (el) el.srcObject = remoteStreams[0]; }}
              autoPlay
              className="main-video"
            ></video>
          ) : (
            <div className="no-participants"><PersonIcon /><p>No other participants</p></div>
          )}
        </div>

        {/* ✅ Student video strip */}
        {remoteStreams.length > 1 && (
          <div className="student-videos-scroll">
            {remoteStreams.slice(1).map((stream, i) => (
              <video
                key={i}
                ref={el => { if (el) el.srcObject = stream; }}
                autoPlay
                className="student-video"
              ></video>
            ))}
          </div>
        )}

        {/* Local video */}
        <div className="local-video">
          <video ref={localVideoRef} autoPlay muted className="thumbnail-video"></video>
          {showEmoji && <div className="emoji-overlay">{emoji}</div>}
          {handRaised && <PanToolAltIcon className="hand-raised-icon" />}
        </div>
      </div>

      {/* Controls */}
      <div className="meeting-controls">
        {isTeacher ? (
          <>
            <button onClick={toggleAudio} className="control-button">{audioEnabled ? <MicIcon /> : <MicOffIcon />}</button>
            <button onClick={toggleVideo} className="control-button">{videoEnabled ? <VideocamIcon /> : <VideocamOffIcon />}</button>
            <button onClick={toggleScreenShare} className="control-button">{screenSharing ? <StopScreenShareIcon /> : <ScreenShareIcon />}</button>
          </>
        ) : (
          <>
            <button className="control-button disabled"><MicOffIcon /><span>Muted</span></button>
            <button className="control-button disabled"><VideocamIcon /><span>Camera</span></button>
          </>
        )}

        <button onClick={() => setChatOpen(!chatOpen)} className="control-button"><ChatBubbleOutlineIcon /></button>
        {!isTeacher && <button onClick={handleRaiseHand} className="control-button"><PanToolAltIcon /></button>}
        <button onClick={() => handleEmoji('👍')} className="control-button"><EmojiEmotionsIcon /></button>
        <button onClick={() => handleEmoji('👏')} className="control-button"><EmojiEmotionsIcon /></button>
        <button onClick={leaveCall} className="control-button leave-button"><CallEndIcon /><span>Leave</span></button>
      </div>

      {/* Participants */}
      <div className="participants-info">
        <GroupsIcon /><span>Participants: {participants.length}</span>
      </div>

      {/* ✅ Teacher sees raised hands */}
      {isTeacher && participants.some(p => p.handRaised) && (
        <div className="raised-hands-panel">
          <h4>Raised Hands</h4>
          {participants.filter(p => p.handRaised).map(p => (
            <div key={p.id} className="student-box">
              <span>{p.name}</span>
              <button onClick={() => unmuteStudent(p.id)}>Unmute</button>
            </div>
          ))}
        </div>
      )}

      {/* Chat */}
      {chatOpen && (
        <div className="chat-sidebar">
          <div className="chat-header">
            <h4>In-call messages</h4>
            <button onClick={() => setChatOpen(false)}>×</button>
          </div>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className="message"><b>{m.sender}</b>: {m.message} <small>{m.timestamp}</small></div>
            ))}
          </div>
          <div className="chat-input-container">
            <input type="text" value={messageInput} onChange={(e) => setMessageInput(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && sendMessage()} />
            <button onClick={sendMessage}>↑</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveClassPage;
