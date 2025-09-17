import React, { useState, useRef, useEffect } from 'react';
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
import EmojiEmotionsIcon from '@mui/icons-material/EmojiEmotions';
import PanToolAltIcon from '@mui/icons-material/PanToolAlt';
import GroupsIcon from '@mui/icons-material/Groups';
import { useSelector } from 'react-redux';

const configuration = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

const StudentVideo = ({ stream, name }) => {
  const ref = useRef();
  useEffect(() => {
    if (ref.current) {
      ref.current.srcObject = stream || null;
      ref.current.muted = !!(stream && stream.getAudioTracks && stream.getAudioTracks().length === 0);
      ref.current.play().catch((err) => console.error('Video play error:', err));
    }
    console.log('StudentVideo stream updated for', name, stream);
  }, [stream]);
  return (
    <div className="student-video-container">
      <video ref={ref} autoPlay playsInline className="student-video" />
      <div className="video-label">{name}</div>
    </div>
  );
};

const LiveClassPage = () => {
  const { courseId } = useParams();
  const { user, token } = useSelector((state) => state.auth);
  const isTeacher = user?.role === 'teacher';

  const ws = useRef(null);

  // States
  const [joined, setJoined] = useState(false);
  const [localStream, setLocalStream] = useState(null);
  const [screenStream, setScreenStream] = useState(null);
  const [remoteStreams, setRemoteStreams] = useState({});
  const [peerConnections, setPeerConnections] = useState({});
  const [videoEnabled, setVideoEnabled] = useState(true);
  const [audioEnabled, setAudioEnabled] = useState(isTeacher);
  const [screenSharing, setScreenSharing] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [participantsOpen, setParticipantsOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [messageInput, setMessageInput] = useState('');
  const [meetingTime, setMeetingTime] = useState('00:00:00');
  const [participants, setParticipants] = useState([]);
  const [showEmoji, setShowEmoji] = useState(false);
  const [emoji, setEmoji] = useState('');
  const [handRaised, setHandRaised] = useState(false);
  const [mediaError, setMediaError] = useState(null);

  // Refs
  const localVideoRef = useRef();
  const mainVideoRef = useRef();
  const screenShareVideoRef = useRef();
  const meetingTimer = useRef();

  useEffect(() => {
    if (!joined) {
      initializePreview();
    }
    return () => {
      if (localStream) localStream.getTracks().forEach((track) => track.stop());
      if (screenStream) screenStream.getTracks().forEach((track) => track.stop());
      if (meetingTimer.current) clearInterval(meetingTimer.current);
    };
  }, [joined]);

  useEffect(() => {
    if (screenSharing && screenStream && screenShareVideoRef.current) {
      screenShareVideoRef.current.srcObject = screenStream;
      screenShareVideoRef.current.muted = true;
      screenShareVideoRef.current.play().catch((err) => console.error('Screen share play error:', err));
    }
  }, [screenSharing, screenStream]);

  const initializePreview = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      setLocalStream(stream);
      setMediaError(null);
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        localVideoRef.current.play().catch((err) => console.error('Local video play error:', err));
      }
      if (!isTeacher) {
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
          audioTrack.enabled = false;
          setAudioEnabled(false);
        }
      }
      const videoTrack = stream.getVideoTracks()[0];
      if (videoTrack) videoTrack.enabled = videoEnabled;
    } catch (error) {
      console.error('Error accessing media devices:', error);
      if (error.name === 'NotReadableError') {
        setMediaError('Camera or microphone is in use by another application. Please close other apps or tabs and try again.');
      } else {
        setMediaError(`Failed to access camera/microphone: ${error.message}`);
      }
    }
  };

  const initializeMeetingMedia = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      setLocalStream(stream);
      setMediaError(null);
      if (localVideoRef.current) {
        localVideoRef.current.srcObject = stream;
        localVideoRef.current.play().catch((err) => console.error('Local video play error:', err));
      }
      if (!isTeacher) {
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
          audioTrack.enabled = false;
          setAudioEnabled(false);
        }
      }
      startMeetingTimer();
    } catch (error) {
      console.error('Error accessing media devices:', error);
      if (error.name === 'NotReadableError') {
        setMediaError('Camera or microphone is in use by another application. Please close other apps or tabs and try again.');
      } else {
        setMediaError(`Failed to access camera/microphone: ${error.message}`);
      }
    }
  };  

  const connectWebSocket = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://192.168.0.20:8000/ws/class/${encodeURIComponent(7)}/?token=Bearer%20${encodeURIComponent(token)}`;
    console.log('Connecting to WebSocket:', wsUrl);
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      console.log('WebSocket connected');
      ws.current.send(JSON.stringify({ type: 'join', userId: user?.id, user: user?.name || 'Guest' }));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('WebSocket message received:', data);


      switch (data.type) {
        case 'signaling':
          handleSignaling(data.data, data.sender);
          break;
        case 'chat':
          setMessages((prev) => [
            ...prev,
            { sender: data.sender, message: data.message, timestamp: new Date().toLocaleTimeString(), is_emoji: data.is_emoji },
          ]);
          break;
        case 'participants_message':
          console.log('Participants updated:', data.participants);
          setParticipants(data.participants);
          break;
        case 'raise-hand':
          if (isTeacher) {
            setParticipants((prev) =>
              prev.map((p) => (p.id === data.userId ? { ...p, handRaised: true } : p))
            );
          } else if (data.userId === user.id) {
            setHandRaised(true);
          }
          break;
        case 'unmute':
          if (!isTeacher && data.userId === user.id) {
            const audioTrack = localStream?.getAudioTracks()[0];
            if (audioTrack) {
              audioTrack.enabled = true;
              setAudioEnabled(true);
            }
          }
          if (isTeacher) {
            setParticipants((prev) =>
              prev.map((p) => (p.id === data.userId ? { ...p, handRaised: false } : p))
            );
          }
          break;
        case 'share':
          console.log('Screen share update:', data);
          setParticipants((prev) =>
            prev.map((p) => (p.id === data.userId ? { ...p, isSharing: data.isSharing } : p))
          );
          break;
        default:
          break;
      }
    };

    ws.current.onclose = () => {
      console.log('WebSocket closed');
    };

    ws.current.onerror = (err) => {
      console.error('WebSocket error:', err);
    };
  };

  const createPeerConnection = (otherId) => {
    console.log('Creating peer connection for:', otherId);
    const pc = new RTCPeerConnection(configuration);
    pc.__remoteUserId = otherId;

    pc.onicecandidate = (event) => {
      if (event.candidate) {
        console.log('Sending ICE candidate to:', otherId);
        ws.current?.send(
          JSON.stringify({
            type: 'signaling',
            data: { type: 'candidate', candidate: event.candidate },
            target: otherId,
          })
        );
      }
    };

    pc.ontrack = (event) => {
      const [stream] = event.streams;
      const remoteUserId = pc.__remoteUserId;

      setRemoteStreams((prev) => {
        const existing = prev[remoteUserId] || {};
        if (event.track.kind === 'video') {
          const isScreen =
            (event.track.label && event.track.label.toLowerCase().includes('screen')) ||
            event.track.contentHint === 'screen';
          console.log(`Received ${isScreen ? 'screen' : 'camera'} video track from user:`, remoteUserId);
          return {
            ...prev,
            [remoteUserId]: {
              ...existing,
              [isScreen ? 'screen' : 'camera']: stream,
            },
          };
        }
        if (event.track.kind === 'audio') {
          return {
            ...prev,
            [remoteUserId]: {
              ...existing,
              audio: stream,
            },
          };
        }
        return prev;
      });
    };

    if (localStream) {
      localStream.getTracks().forEach((track) => {
        console.log('Adding track to peer connection:', track.kind, 'for:', otherId);
        pc.addTrack(track, localStream);
      });
    }

    setPeerConnections((prev) => ({ ...prev, [otherId]: pc }));
    return pc;
  };

  const shouldInitiate = (myId, otherId) => myId > otherId;

  useEffect(() => {
    if (joined && localStream) {
      participants.forEach((p) => {
        if (p.id !== user.id && !peerConnections[p.id]) {
          const pc = createPeerConnection(p.id);
          if (shouldInitiate(user.id, p.id)) {
            console.log('Initiating offer to:', p.id);
            pc.createOffer()
              .then((offer) => pc.setLocalDescription(offer))
              .then(() => {
                ws.current?.send(
                  JSON.stringify({
                    type: 'signaling',
                    data: { type: 'offer', offer: pc.localDescription },
                    target: p.id,
                  })
                );
              })
              .catch((err) => console.error('Error creating offer:', err));
          }
        }
      });
    }
  }, [participants, joined, localStream, user.id]);

  const handleSignaling = async (innerData, sender) => {
    sender = parseInt(sender);
    console.log('Handling signaling from:', sender, 'type:', innerData.type);
    let pc = peerConnections[sender];
    if (!pc) {
      pc = createPeerConnection(sender);
    }

    try {
      switch (innerData.type) {
        case 'offer':
          await pc.setRemoteDescription(new RTCSessionDescription(innerData.offer));
          const answer = await pc.createAnswer();
          await pc.setLocalDescription(answer);
          ws.current?.send(
            JSON.stringify({
              type: 'signaling',
              data: { type: 'answer', answer: pc.localDescription },
              target: sender,
            })
          );
          if (pc.pendingCandidates && pc.remoteDescription) processPendingCandidates(pc, sender);
          break;
        case 'answer':
          await pc.setRemoteDescription(new RTCSessionDescription(innerData.answer));
          if (pc.pendingCandidates && pc.remoteDescription) processPendingCandidates(pc, sender);
          break;
        case 'candidate':
          if (pc.remoteDescription) {
            await pc.addIceCandidate(new RTCIceCandidate(innerData.candidate)).catch((err) =>
              console.error('Error adding ICE candidate:', err)
            );
          } else {
            pc.pendingCandidates = pc.pendingCandidates || [];
            pc.pendingCandidates.push(innerData.candidate);
          }
          break;
        default:
          break;
      }
    } catch (err) {
      console.error('Signaling error:', err);
    }
  };

  const processPendingCandidates = (pc, sender) => {
    if (pc.pendingCandidates && pc.remoteDescription) {
      pc.pendingCandidates.forEach((candidate) => {
        pc.addIceCandidate(new RTCIceCandidate(candidate)).catch((err) =>
          console.error('Error processing pending candidate:', err)
        );
      });
      delete pc.pendingCandidates;
    }
  };

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

  if (!screenSharing) {
    try {
      const newScreenStream = await navigator.mediaDevices.getDisplayMedia({
        video: { cursor: 'always' },
        audio: false,
      });
      setScreenStream(newScreenStream);
      const screenTrack = newScreenStream.getVideoTracks()[0];

      await Promise.all(
        Object.entries(peerConnections).map(async ([otherId, pc]) => {
          try {
            pc.getSenders()
              .filter((s) => s.track && s.track.kind === 'video')
              .forEach((sender) => pc.removeTrack(sender));
            pc.addTrack(screenTrack, newScreenStream);
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            ws.current?.send(JSON.stringify({
              type: 'signaling',
              data: { type: 'offer', offer: pc.localDescription },
              target: otherId,
            }));
          } catch (err) {
            console.error('Error adding screen track for', otherId, err);
          }
        })
      );

      setScreenSharing(true);
      ws.current?.send(JSON.stringify({
        type: 'share',
        userId: user.id,
        isSharing: true,
      }));

      screenTrack.onended = () => toggleScreenShare();
    } catch (err) {
      console.error('Screen share initiation error:', err);
      setMediaError('Failed to start screen share. Please try again.');
    }
  } else {
    try {
      await Promise.all(
        Object.entries(peerConnections).map(async ([otherId, pc]) => {
          try {
            pc.getSenders()
              .filter((s) => s.track && s.track.kind === 'video')
              .forEach((sender) => pc.removeTrack(sender));
            if (localStream) {
              const cameraTrack = localStream.getVideoTracks()[0];
              if (cameraTrack) {
                pc.addTrack(cameraTrack, localStream);
              }
            }
            const offer = await pc.createOffer();
            await pc.setLocalDescription(offer);
            ws.current?.send(JSON.stringify({
              type: 'signaling',
              data: { type: 'offer', offer: pc.localDescription },
              target: otherId,
            }));
          } catch (err) {
            console.error('Error restoring camera track for', otherId, err);
          }
        })
      );

      if (screenStream) {
        screenStream.getTracks().forEach((t) => t.stop());
        setScreenStream(null);
      }

      setScreenSharing(false);
      ws.current?.send(JSON.stringify({
        type: 'share',
        userId: user.id,
        isSharing: false,
      }));
    } catch (err) {
      console.error('Screen share stop error:', err);
      setMediaError('Failed to stop screen share. Please try again.');
    }
  }
};

  const sendMessage = () => {
    if (messageInput.trim()) {
      const newMessage = {
        id: Date.now(),
        message: messageInput,
        sender: user?.name || 'You',
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages([...messages, newMessage]);
      ws.current?.send(JSON.stringify({ type: 'chat', message: messageInput }));
      setMessageInput('');
    }
  };

  const joinMeeting = () => {
    setJoined(true);
    connectWebSocket();
    initializeMeetingMedia();
  };

  const leaveCall = () => {
    if (localStream) localStream.getTracks().forEach((track) => track.stop());
    if (screenStream) screenStream.getTracks().forEach((track) => track.stop());
    if (meetingTimer.current) clearInterval(meetingTimer.current);
    Object.values(peerConnections).forEach((pc) => pc.close());
    if (ws.current) {
      ws.current.close();
      ws.current = null;
    }
    setJoined(false);
    setScreenSharing(false);
    setHandRaised(false);
    setShowEmoji(false);
    setEmoji('');
    setPeerConnections({});
    setRemoteStreams({});
    setParticipants([]);
    setMediaError(null);
  };

  const handleRaiseHand = () => {
    ws.current?.send(JSON.stringify({ type: 'raise-hand', userId: user.id }));
  };

  const unmuteStudent = (studentId) => {
    ws.current?.send(JSON.stringify({ type: 'unmute', userId: studentId }));
  };

  const handleEmoji = (emojiVal) => {
    setShowEmoji(true);
    setEmoji(emojiVal);
    ws.current?.send(JSON.stringify({ type: 'emoji', emoji: emojiVal }));
    setTimeout(() => {
      setShowEmoji(false);
      setEmoji('');
    }, 2000);
  };

  const teacher = participants.find((p) => p.role === 'teacher');
  const teacherId = teacher?.id;
  const teacherSharing = teacher?.isSharing || false;

  let mainStream;
  let mainName = '';
  if (isTeacher) {
    mainStream = screenSharing && screenStream ? screenStream : localStream;
    mainName = 'You (Teacher)';
  } else if (teacherId && remoteStreams[teacherId]) {
    mainStream = teacherSharing && remoteStreams[teacherId].screen ? remoteStreams[teacherId].screen : remoteStreams[teacherId].camera;
    mainName = `Teacher: ${teacher.name}`;
  } else {
    mainStream = null;
    mainName = '';
  }

  const studentStreams = participants
    .filter((p) => p.id !== user.id && p.id !== teacherId)
    .map((p) => ({ id: p.id, name: p.name, isSharing: !!p.isSharing }));

  useEffect(() => {
    if (mainVideoRef.current) {
      if (mainStream) {
        console.log('Setting main video stream:', mainStream);
        mainVideoRef.current.srcObject = mainStream;
        mainVideoRef.current.play().catch((err) => console.error('Main video play error:', err));
      } else {
        mainVideoRef.current.srcObject = null;
      }
    }
  }, [mainStream]);
console.log("participants",participants);
  if (!joined) {
    return (
      <div className="prejoin-container">
        <div className="prejoin-header">
          <div className="google-meet-logo">Live Meet</div>
          <div className="meeting-info">
            <h2>{user?.name}</h2>
            <p>Do you want people to see and hear you in the meeting?</p>
            {mediaError && <p className="error-message" style={{ color: 'red' }}>{mediaError}</p>}
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
          <button onClick={joinMeeting} className="join-button">
            Join now
          </button>
          <div className="meeting-id">Meeting ID: {courseId}</div>
        </div>
      </div>
    );
  }
  console.log('Rendering main meeting UI', studentStreams, remoteStreams);
  return (
    <div className="meeting-container">
      <div className="meeting-header">
        <div className="meeting-info-header">
          <span className="meeting-time">{meetingTime}</span>
          <span className="meeting-id-header">Meeting ID: {courseId}</span>
          <span className="user-role">({user?.role})</span>
        </div>
        <div className="meeting-title">{user?.name} (You, {screenSharing ? 'presenting' : 'joined'})</div>
        {mediaError && <p className="error-message" style={{ color: 'red' }}>{mediaError}</p>}
      </div>

      <div className="video-container">
        <div className="remote-video">
          {/* {screenSharing && screenStream && isTeacher ? ( */}
            <div className="main-video-container">
              <video ref={screenShareVideoRef} autoPlay muted className="main-video"></video>
              <div className="video-label">{mainName}</div>
            </div>
          {/* ) */}
            {/* //  : (
            //   <div className="main-video-container">
            //     <video ref={mainVideoRef} autoPlay playsInline muted={isTeacher} className="main-video" />
            //     <div className="video-label">{mainName}</div>
            //   </div>
            // )} */}
        </div>

        {studentStreams.length > 0 && (
          <div className="student-videos-scroll">
            {studentStreams.map(({ id, name, isSharing }) => {
              const userStreams = remoteStreams[id] || {};
              const stream = isSharing && userStreams.screen ? userStreams.screen : userStreams.camera;
              return <StudentVideo key={id} stream={stream} name={name} />;
            })}
          </div>
        )}

        <div className="local-video">
          <video ref={localVideoRef} autoPlay muted className="thumbnail-video"></video>
          <div className="video-label">You</div>
          {showEmoji && <div className="emoji-overlay">{emoji}</div>}
          {handRaised && <PanToolAltIcon className="hand-raised-icon" />}
        </div>
      </div>

      <div className="meeting-controls">
        {isTeacher ? (
          <>
            <button onClick={toggleAudio} className="control-button">
              {audioEnabled ? <MicIcon /> : <MicOffIcon />}
            </button>
            <button onClick={toggleVideo} className="control-button">
              {videoEnabled ? <VideocamIcon /> : <VideocamOffIcon />}
            </button>
            <button onClick={toggleScreenShare} className="control-button">
              {screenSharing ? <StopScreenShareIcon /> : <ScreenShareIcon />}
            </button>
          </>
        ) : (
          <>
            <button className="control-button disabled">
              <MicOffIcon />
              <span>Muted</span>
            </button>
            <button onClick={toggleVideo} className="control-button">
              {videoEnabled ? <VideocamIcon /> : <VideocamOffIcon />}
            </button>
            <button onClick={toggleScreenShare} className="control-button">
              {screenSharing ? <StopScreenShareIcon /> : <ScreenShareIcon />}
            </button>
          </>
        )}

        <button onClick={() => setChatOpen(!chatOpen)} className="control-button">
          <ChatBubbleOutlineIcon />
        </button>
        {!isTeacher && (
          <button onClick={handleRaiseHand} className="control-button">
            <PanToolAltIcon />
          </button>
        )}
        <button onClick={() => handleEmoji('👍')} className="control-button">
          <EmojiEmotionsIcon />
        </button>
        <button onClick={() => handleEmoji('👏')} className="control-button">
          <EmojiEmotionsIcon />
        </button>
        <button onClick={() => setParticipantsOpen(!participantsOpen)} className="control-button">
          <GroupsIcon />
        </button>
        <button onClick={leaveCall} className="control-button leave-button">
          <CallEndIcon />
          <span>Leave</span>
        </button>
      </div>

      <div className="participants-info">
        <GroupsIcon />
        <span>Participants: {participants.length}</span>
      </div>

      {isTeacher && participants.some((p) => p.handRaised) && (
        <div className="raised-hands-panel">
          <h4>Raised Hands</h4>
          {participants
            .filter((p) => p.handRaised)
            .map((p) => (
              <div key={p.id} className="student-box">
                <span>{p.name}</span>
                <button onClick={() => unmuteStudent(p.id)}>Unmute</button>
              </div>
            ))}
        </div>
      )}

      {chatOpen && (
        <div className="chat-sidebar">
          <div className="chat-header">
            <h4>In-call messages</h4>
            <button onClick={() => setChatOpen(false)}>×</button>
          </div>
          <div className="chat-messages">
            {messages.map((m, i) => (
              <div key={i} className="message">
                <b>{m.sender}</b>: {m.message} <small>{m.timestamp}</small>
              </div>
            ))}
          </div>
          <div className="chat-input-container">
            <input
              type="text"
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            />
            <button onClick={sendMessage}>↑</button>
          </div>
        </div>
      )}

      {participantsOpen && (
        <div className="participants-sidebar">
          <div className="participants-header">
            <h4>Participants ({participants.length})</h4>
            <button onClick={() => setParticipantsOpen(false)}>×</button>
          </div>
          <div className="participants-list">
            {participants.map((p, i) => (
              <div key={i} className="participant-item">
                <b>{p.name}jjj</b> ({p.role}) {p.handRaised && <PanToolAltIcon />} {p.isSharing && '(sharing)'}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default LiveClassPage;