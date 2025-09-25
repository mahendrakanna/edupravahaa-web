import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  createRemoteConnection,
  destroyRemoteConnection,
  useRemoteState,
  Timeout,
  toast,
  useLocalState,
  useChatState,
  sendChat,
  startScreenCapture,
  stopScreenCapture,
  startMediaDevice,
  stopMediaDevice,
  dummyAudioDevice,
  dummyVideoDevice,
} from '../../../redux/meetingSlice'
import {
  FaMicrophone,
  FaMicrophoneSlash,
  FaVideo,
  FaVideoSlash,
  FaDesktop,
  FaStop,
  FaCircle,
  FaStopCircle,
  FaUsers,
  FaComments,
  FaExpand,
  FaCompress,
  FaTimes,
  FaSignOutAlt,
  FaHandPaper,
  FaRecordVinyl 
} from 'react-icons/fa'
import './LiveClass.css'
import { useDispatch, useSelector } from "react-redux";
import { uploadRecording } from '../../../redux/recordedVideosSlice'
 
export default function LiveClass() {
  const params = useParams()
  const navigate = useNavigate();
  const dispatch = useDispatch();
  const {user} = useSelector(state => state.auth)
  const isStudent = user.role === 'student'
 
  // console.log("[LiveClass] params:", params,"user",user)
  const [socket, connections] = useRemoteState(state => [state.socket, state.connections])
  const [
    userStream,
    displayStream,
    audioDevices,
    videoDevices,
    currentMicId,
    currentCameraId,
    preferences,
    sidePanelTab,
  ] = useLocalState(state => [
    state.userStream,
    state.displayStream,
    state.audioDevices,
    state.videoDevices,
    state.currentMicId,
    state.currentCameraId,
    state.preferences,
    state.sidePanelTab,
  ])
  const { messages } = useChatState()
 
  const [isFullscreen, setIsFullscreen] = useState(!!document.fullscreenElement)
  const [handRaised, setHandRaised] = useState(false);
  const [raisedHands, setRaisedHands] = useState([]);
  // const [canUnmute, setCanUnmute] = useState(!isStudent)
  useEffect(() => {
    const onFsChange = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', onFsChange)
    return () => document.removeEventListener('fullscreenchange', onFsChange)
  }, [])
  const toggleFullscreen = async () => {
    try {
      if (!document.fullscreenElement) await document.documentElement.requestFullscreen()
      else await document.exitFullscreen()
    } catch {}
  }
 
  const [meetingTime, setMeetingTime] = useState(0)
  useEffect(() => {
    const interval = setInterval(() => setMeetingTime(t => t + 1), 1000)
    return () => clearInterval(interval)
  }, [])
 
  const formatTime = (s) => {
    const h = Math.floor(s / 3600).toString().padStart(2, '0')
    const m = Math.floor((s % 3600) / 60).toString().padStart(2, '0')
    const sec = (s % 60).toString().padStart(2, '0')
    return `${h}:${m}:${sec}`
  }
 
  const [isRecording, setIsRecording] = useState(false)
  const recorderRef = useRef(null)
  const recordedBlobsRef = useRef([])
 
  const [captionsEnabled, setCaptionsEnabled] = useState(false)
  const [presentationAudio, setPresentationAudio] = useState(true)

  // Auto-start recording when teacher joins
  useEffect(() => {
    if (
      user.role === "teacher" &&
      userStream &&
      userStream.getTracks().length > 0 &&
      !isRecording
    ) {
      startRecording();
    }
  }, [user.role, userStream, isRecording]);

 
   useEffect(() => {
  const urlRoomId = params?.roomId;
  const currentRoom = useRemoteState.getState().room;
 
  // Only redirect to landing if there's no room info in state
  if (!currentRoom || currentRoom.id !== urlRoomId) {
    // This means user is not in a session yet, safe to redirect
    navigate(`/live-class/landing/${urlRoomId}`, { replace: true });
  }
}, [params, navigate]);
 
  useEffect(() => {
    // console.log(params?.roomId,"kavya")
    const urlRoomId = params?.roomId
    const currentRoom = useRemoteState.getState().room
    if (urlRoomId && (!currentRoom || currentRoom.id !== urlRoomId)) {
      useRemoteState.setState({ room: { id: urlRoomId, name: 'Live Class' } })
    }
  }, [params])
 
  const remoteVideoItems = useMemo(() =>
    connections
      .filter(c => !c.userStream.empty)
      .map(c => ({ id: c.userId, label: c.userName || 'Guest', stream: c.userStream, isMuted: !c.userStream.getAudioTracks()[0]?.enabled })),
  [connections])
  const remoteScreenItems = useMemo(() =>
    connections
      .filter(c => !c.displayStream.empty)
      .map(c => ({ id: c.userId + ':screen', label: `${c.userName || 'Guest'} (presenting)`, stream: c.displayStream, isMuted: false })),
  [connections])
 
  const hasScreenShare = displayStream && displayStream.getTracks().length > 0
  const localScreenItem = hasScreenShare ? { id: 'local:screen', label: `${preferences.userName || 'You'} (You, presenting)`, stream: displayStream, isMuted: false } : null
  const localVideoItem = { id: 'local:user', label: `${preferences.userName || 'You'} (You)`, stream: userStream, isMuted: !currentMicId, flip: true }
 
  const allVideoItems = [localVideoItem, ...remoteVideoItems]
  const allScreenItems = [localScreenItem, ...remoteScreenItems].filter(Boolean)
 
  const [pinnedId, setPinnedId] = useState(null)
 
  const togglePin = (id) => {
    setPinnedId(pinnedId === id ? null : id)
  }
 
  useEffect(() => {
    if (allScreenItems.length > 0 && !pinnedId) {
      setPinnedId(allScreenItems[0].id)
    } else if (allScreenItems.length === 0 && pinnedId && pinnedId.endsWith(':screen')) {
      setPinnedId(null)
    }
  }, [allScreenItems, pinnedId])
 
  const pinnedItem = useMemo(() => {
    if (!pinnedId) return null
    return [...allVideoItems, ...allScreenItems].find(i => i.id === pinnedId) || null
  }, [pinnedId, allVideoItems, allScreenItems])
 
  const sidebarItems = useMemo(() => {
    return [...allVideoItems, ...allScreenItems].filter(i => i.id !== pinnedId)
  }, [pinnedId, allVideoItems, allScreenItems])
 
  const isScreenPinned = pinnedItem && pinnedItem.id.endsWith(':screen')
 
  // const toggleMic = async () => {
  //   if (user.role === 'student' && !canUnmute) {
  //     toast('You cannot unmute yourself. Raise your hand to request.', { type: 'info', autoClose: Timeout.SHORT });
  //     return;
  //   }
  //   const handleUnmute = async () => {
  //     setCanUnmute(true);
  //     if (!currentMicId) {
  //       const device = audioDevices[0] || dummyAudioDevice;
  //       await startMediaDevice(device);
  //     }
  //   };
  //   const device = audioDevices.find(d => d.deviceId === currentMicId) || audioDevices[0] || dummyAudioDevice;
  //   if (currentMicId) {
  //     stopMediaDevice(device);
  //     if (user.role === 'student') setCanUnmute(false);
  //   } else {
  //     await startMediaDevice(device);
  //   }
  // };
 
  const toggleCam = async () => {
    const device = videoDevices.find(d => d.deviceId === currentCameraId) || videoDevices[0] || dummyVideoDevice
    if (currentCameraId) stopMediaDevice(device)
    else await startMediaDevice(device)
  }
  const toggleScreen = async () => { if (hasScreenShare) stopScreenCapture(); else await startScreenCapture() }
 
  const startRecording = async () => {
    try {
      if (recorderRef.current) return; // already recording

      // Wait until teacher stream is ready
      if (!userStream || userStream.getTracks().length === 0) {
        console.warn("User stream not ready, retrying...");
        setTimeout(startRecording, 1000);
        return;
      }

      //  1. Setup canvas
      const canvas = document.createElement("canvas");
      const ctx = canvas.getContext("2d");
      canvas.width = 1280;
      canvas.height = 720;

      let activeVideoTrack =
        displayStream?.getVideoTracks()[0] || userStream?.getVideoTracks()[0];

      const videoEl = document.createElement("video");
      videoEl.srcObject = new MediaStream([activeVideoTrack]);
      videoEl.muted = true;
      await videoEl.play();

      const drawFrame = () => {
        if (activeVideoTrack && videoEl.readyState >= 2) {
          ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);
        }
        requestAnimationFrame(drawFrame);
      };
      drawFrame();

      const canvasStream = canvas.captureStream(30);

      //  2. Mix teacher + students audio
      const audioCtx = new AudioContext();
      const destination = audioCtx.createMediaStreamDestination();

      const addAudio = (stream) => {
        if (!stream) return;
        stream.getAudioTracks().forEach((track) => {
          const src = audioCtx.createMediaStreamSource(new MediaStream([track]));
          src.connect(destination);
        });
      };

      addAudio(userStream); // teacher mic
      connections.forEach((c) => addAudio(c.userStream)); // students mics

      //  3. Combine video + audio
      const mixedStream = new MediaStream([
        ...canvasStream.getVideoTracks(),
        ...destination.stream.getAudioTracks(),
      ]);

      //  4. Setup MediaRecorder
      recordedBlobsRef.current = [];
      const mr = new MediaRecorder(mixedStream, {
        mimeType: "video/webm;codecs=vp9,opus",
      });

      mr.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) recordedBlobsRef.current.push(e.data);
      };

      mr.onstop = async () => {
        const blob = new Blob(recordedBlobsRef.current, { type: "video/webm" });

        dispatch(
          uploadRecording({
            roomId: params.roomId,
            userId: user.id,
            blob,
          })
        );
      };

      mr.start();
      recorderRef.current = mr;
      setIsRecording(true);
      toast("Recording started", { autoClose: Timeout.SHORT });

      // 🔄 5. Handle screen <-> camera switching
      const updateActiveVideo = () => {
        const newTrack =
          displayStream?.getVideoTracks()[0] || userStream?.getVideoTracks()[0];
        if (newTrack && newTrack !== activeVideoTrack) {
          activeVideoTrack = newTrack;
          videoEl.srcObject = new MediaStream([activeVideoTrack]);
          videoEl.play();
        }
      };
 
      // react to screen share stop
      const screenTrack = displayStream?.getVideoTracks()[0];
      if (screenTrack) {
        screenTrack.onended = updateActiveVideo;
      }
      // poll for changes
      setInterval(updateActiveVideo, 2000);
    } catch (err) {
      console.error("Recording error:", err);
      toast("Recording failed", { type: "error" });
    }
  };

  const stopRecording = () => {
    const mr = recorderRef.current;
    if (mr && mr.state !== "inactive") {
      mr.stop();
      recorderRef.current = null;
      setIsRecording(false);
      toast("Recording saved", { autoClose: Timeout.SHORT });
    }
  }
 
  const leaveMeeting = () => {
    if (user.role === "teacher" && isRecording) {
      stopRecording(); // stops & uploads
    }
    stopScreenCapture();
    audioDevices.forEach(stopMediaDevice);
    videoDevices.forEach(stopMediaDevice);
    connections.forEach(destroyRemoteConnection);
    if (socket) socket.close();
    window.history.back();
  };

 
  const [chatText, setChatText] = useState('')
  const sendChatMessage = () => {
    const text = chatText.trim()
    if (!text) return
    sendChat({ id: String(Date.now()), text, userLabel: preferences.userName || 'You', mine: true })
    setChatText('')
  }
 
  const openPanel = tab => useLocalState.setState({ sidePanelTab: tab })
  const closePanel = () => useLocalState.setState({ sidePanelTab: undefined })
 
  const hasAnyScreenShare = allScreenItems.length > 0
 
  const presentingLabel = allScreenItems[0]?.label || 'Presenting'
  // console.log("connections",connections)
 
  // useEffect(() => {
  //   if (!socket) return;
 
  //   const handleRaisedHandsUpdate = ({ raisedHands }) => {
  //     console.log('Received raisedHands update:', raisedHands); // Debug: Log the full received list
  //     setRaisedHands(raisedHands);
  //     const isSelfRaised = raisedHands.some(r => r.userId === socket.id);
  //     setHandRaised(isSelfRaised);
  //   };
 
  //   const handleUnmute = async () => {
  //     setCanUnmute(true);
  //     try {
  //       const device = audioDevices[0] || dummyAudioDevice;
  //       await startMediaDevice(device);
  //       toast('You have been unmuted by the teacher', { type: 'info', autoClose: Timeout.SHORT });
  //     } catch (err) {
  //       console.error("Failed to start mic:", err);
  //       toast('Cannot access microphone', { type: 'error' });
  //     }
  //   };
 
  //   const handleMute = () => {
  //     setCanUnmute(false);
  //     if (currentMicId) {
  //       const device = audioDevices.find(d => d.deviceId === currentMicId) || dummyAudioDevice;
  //       stopMediaDevice(device);
  //     }
  //   };
 
  //   socket.on('action:raised_hands_update', handleRaisedHandsUpdate);
  //   socket.on('action:unmute', handleUnmute);
  //   socket.on('action:mute', handleMute);
 
  //   return () => {
  //     socket.off('action:raised_hands_update', handleRaisedHandsUpdate);
  //     socket.off('action:unmute', handleUnmute);
  //     socket.off('action:mute', handleMute);
  //   };
  // }, [socket, currentMicId, audioDevices, canUnmute]);
 
  const toggleHandRaise = () => {
    if (!isStudent) return;
    const newRaised = !handRaised;
    setHandRaised(newRaised);
    socket.emit('request:raise_hand', { roomId: params.roomId, raised: newRaised });
  };
 
  const toggleMuteUser = (userId, isMuted) => {
    if (isStudent) return;
    const action = isMuted ? 'unmute_user' : 'mute_user';
    console.log('[LiveClass] Teacher toggling mute:', { userId, action, roomId: params.roomId, userRole: user.role, connections: connections.map(c => ({ userId: c.userId, userName: c.userName })) });
    socket.emit(`request:${action}`, { roomId: params.roomId, userId });
  };
 
  useEffect(() => {
    if (!socket) return;
 
    const handleRaisedHandsUpdate = ({ raisedHands }) => {
      console.log('[LiveClass] Received raisedHands update:', raisedHands);
      setRaisedHands(raisedHands);
      const isSelfRaised = raisedHands.some(r => r.userId === socket.id);
      // console.log('[LiveClass] Self hand raised check:', { socketId: socket.id, isSelfRaised });
      setHandRaised(isSelfRaised);
    };
 
    const handleUnmute = async () => {
      // console.log('[LiveClass] Received unmute action for student:', { socketId: socket.id, audioDevices: audioDevices.map(d => d.deviceId), currentMicId });
      try {
        const device = audioDevices[0] || dummyAudioDevice;
        // console.log('[LiveClass] Attempting to start mic:', { deviceId: device.deviceId });
        await startMediaDevice(device);
        toast('You have been unmuted by the teacher', { type: 'info', autoClose: Timeout.SHORT });
      } catch (err) {
        // console.error('[LiveClass] Failed to start mic:', err);
        toast('Cannot access microphone', { type: 'error' });
      }
    };
 
 
    const handleMute = () => {
      // console.log('[LiveClass] Received mute action for student:', { socketId: socket.id });
      if (currentMicId) {
        const device = audioDevices.find(d => d.deviceId === currentMicId) || dummyAudioDevice;
        stopMediaDevice(device);
      }
    };
 
    socket.on('action:raised_hands_update', handleRaisedHandsUpdate);
    socket.on('action:unmute', handleUnmute);
    socket.on('action:mute', handleMute);
 
    return () => {
      socket.off('action:raised_hands_update', handleRaisedHandsUpdate);
      socket.off('action:unmute', handleUnmute);
      socket.off('action:mute', handleMute);
    };
  }, [socket, currentMicId, audioDevices]);
 
  const toggleMic = async () => {
    if (user.role === 'student' && !currentMicId) {
      console.log('[LiveClass] Student attempted to unmute, blocked:', { socketId: socket.id }); // Debug: Log blocked unmute
      toast('You cannot unmute yourself. Ask the teacher to unmute you.', { type: 'info', autoClose: Timeout.SHORT });
      return;
    }
    const device = audioDevices.find(d => d.deviceId === currentMicId) || audioDevices[0] || dummyAudioDevice;
    if (currentMicId) {
      console.log('[LiveClass] Toggling mic off:', { deviceId: device.deviceId, userRole: user.role }); // Debug: Log mic toggle off
      stopMediaDevice(device);
    } else {
      console.log('[LiveClass] Toggling mic on:', { deviceId: device.deviceId, userRole: user.role }); // Debug: Log mic toggle on
      await startMediaDevice(device);
    }
  };
  const micTitle = user.role !== 'student'
    ? (currentMicId ? 'Mute microphone' : 'Unmute microphone')
    : (currentMicId ? 'Mute microphone' : 'You cannot unmute yourself. Ask the teacher to unmute you.');
 
  return (
    <div className="meet-container">
        <header className="top-bar">
              <div className="meeting-info">
                <h1 className="meeting-title">Edu Pravaha</h1>
                <div className="meeting-meta">
                  <span className="meeting-time">{formatTime(meetingTime)}</span>
                  <span className="meeting-id">ID: {params.roomId || 'student'}</span>
            {isRecording && (
              <span className="recording-indicator">
                <FaRecordVinyl className="recording-icon" />
                Recording
              </span>
            )}
                </div>
              </div>
              <div className="top-controls">
                {hasAnyScreenShare && (
                  <>
                  <span>{presentingLabel}</span>
                    <label className="presentation-audio">
                      <input
                        type="checkbox"
                        checked={presentationAudio}
                        onChange={() => setPresentationAudio(!presentationAudio)}
                      />
                      Presentation audio
                    </label>
                    <button onClick={toggleScreen} className="stop-presenting">
                      Stop presenting
                    </button>
                  </>
                )}
                <button
                  onClick={() => openPanel('people')}
                  className={`top-btn ${sidePanelTab === 'people' ? 'active' : ''}`}
                  title="Participants"
                >
                  <FaUsers />
                  <span className="participant-count">{connections.length + 1}</span>
                </button>
                <button
                  onClick={() => openPanel('chats')}
                  className={`top-btn ${sidePanelTab === 'chats' ? 'active' : ''}`}
                  title="Chat"
                >
                  <FaComments />
                  {messages.length > 0 && <span className="chat-indicator"></span>}
                </button>
                <button
                  onClick={toggleFullscreen}
                  className="top-btn"
                  title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
                >
                  {isFullscreen ? <FaCompress /> : <FaExpand />}
                </button>
              </div>
            </header>
 
      <main className="meet-main">
        <div className="video-area">
          {pinnedItem ? (
            <div className="pinned-video">
              <VideoBox
                stream={pinnedItem.stream}
                label={pinnedItem.label}
                muted={pinnedItem.muted}
                flip={pinnedItem.flip || false}
                onPin={togglePin}
                pinned={true}
                id={pinnedItem.id}
                isMuted={pinnedItem.isMuted}
              />
            </div>
          ) : (
            <div className="grid-videos">
              {allScreenItems.map(item => (
                <VideoBox key={item.id} {...item} onPin={togglePin} onDisconnect={item.id.startsWith('local') ? null : () => disconnectById(item.id)} />
              ))}
              {allVideoItems.map(item => (
                <VideoBox key={item.id} {...item} onPin={togglePin} onDisconnect={item.id.startsWith('local') ? null : () => disconnectById(item.id)} />
              ))}
            </div>
          )}
          {pinnedItem && sidebarItems.length > 0 && (
            <div className="sidebar-videos">
              {sidebarItems.map(item => (
                <VideoBox key={item.id} {...item} onPin={togglePin} onDisconnect={item.id.startsWith('local') ? null : () => disconnectById(item.id)} sidebar />
              ))}
            </div>
          )}
        </div>
 
        {sidePanelTab && (
          <aside className="side-panel">
            <div className="panel-header">
              <strong>{sidePanelTab.charAt(0).toUpperCase() + sidePanelTab.slice(1)}</strong>
              <button onClick={closePanel} className="close-btn"><FaTimes /></button>
            </div>
              {sidePanelTab === 'chats' ? (
                <div className="chat-panel">
                  <div className="chat-messages">
                    {messages.length === 0 ? (
                      <div className="no-messages">
                        <FaComments className="no-messages-icon" />
                        <p>No messages yet</p>
                        <small>Start the conversation!</small>
                      </div>
                    ) : (
                      messages.map((m) => (
                        <div key={m.id} className={`chat-message ${m.mine ? 'mine' : 'other'}`}>
                          <div className="message-avatar">{m.userLabel[0].toUpperCase()}</div>
                          <div className="message-content">
                            {!m.mine && <div className="message-sender">{m.userLabel}</div>}
                            <div className="message-text">{m.text}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  <div className="chat-input-container">
                    <input
                      value={chatText}
                      onChange={(e) => setChatText(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendChatMessage()}
                      placeholder="Type a message..."
                      className="chat-input"
                    />
                    <button onClick={sendChatMessage} className="send-btn" disabled={!chatText.trim()}>
                      Send
                    </button>
                  </div>
                </div>
              ) :  (
              // <div className="participants-panel">
              //   <div className="participant-item self">
              //     <div className="participant-avatar">{(preferences.userName || 'You')[0].toUpperCase()}</div>
              //     <div className="participant-info">
              //       <div className="participant-name">{preferences.userName || 'You'}</div>
              //       <div className="participant-status">You</div>
              //     </div>
              //     <div className="participant-controls">
              //       {currentMicId ? <FaMicrophone className="status-icon" /> : <FaMicrophoneSlash className="status-icon muted" />}
              //       {currentCameraId ? <FaVideo className="status-icon" /> : <FaVideoSlash className="status-icon muted" />}
              //       {handRaised && <FaHandPaper className="status-icon raised" />}
              //     </div>
              //   </div>
              //   {connections.map((c) => {
              //     const isRaised = raisedHands.some(r => r.userId === c.userId);
              //     const isMuted = remoteVideoItems.find((i) => i.id === c.userId)?.isMuted ?? true;
              //     console.log('Participant check:', { userId: c.userId, isRaised, raisedHandsUserIds: raisedHands.map(r => r.userId) }); // Debug: Log per-participant raise check
              //     return (
              //       <div key={c.userId} className="participant-item">
              //         <div className="participant-avatar">{(c.userName || 'Guest')[0].toUpperCase()}</div>
              //         <div className="participant-info">
              //           <div className="participant-name">{c.userName || 'Guest'}</div>
              //           <div className="participant-status">Participant</div>
              //         </div>
              //         <div className="participant-controls">
              //           {isMuted ? (
              //             <FaMicrophoneSlash className="status-icon muted" />
              //           ) : (
              //             <FaMicrophone className="status-icon" />
              //           )}
              //           {isRaised && <FaHandPaper className="status-icon raised" />}
              //           {!isStudent && (
              //             <button
              //               onClick={() => toggleMuteUser(c.userId, isMuted)}
              //               className="mute-btn"
              //             >
              //               {isMuted ? 'Unmute' : 'Mute'}
              //             </button>
              //           )}
              //         </div>
              //       </div>
              //     );
              //   })}
              // </div>
 
 
              // In the return, inside <div className="participants-panel">
              <div className="participants-panel">
                <div className="participant-item self">
                  <div className="participant-avatar">{(preferences.userName || 'You')[0].toUpperCase()}</div>
                  <div className="participant-info">
                    <div className="participant-name">{preferences.userName || 'You'}</div>
                    <div className="participant-status">You</div>
                  </div>
                  <div className="participant-controls">
                    {currentMicId ? <FaMicrophone className="status-icon" /> : <FaMicrophoneSlash className="status-icon muted" />}
                    {currentCameraId ? <FaVideo className="status-icon" /> : <FaVideoSlash className="status-icon muted" />}
                    {handRaised && <FaHandPaper className="status-icon raised" />}
                  </div>
                </div>
                {connections.map((c) => {
                  const isRaised = raisedHands.some(r => r.userId === c.userId);
                  const isMuted = remoteVideoItems.find((i) => i.id === c.userId)?.isMuted ?? true;
                  // console.log('[LiveClass] Participant render:', { userId: c.userId, userName: c.userName, isRaised, isMuted }); // Debug: Log participant details
                  return (
                    <div key={c.userId} className="participant-item">
                      <div className="participant-avatar">{(c.userName || 'Guest')[0].toUpperCase()}</div>
                      <div className="participant-info">
                        <div className="participant-name">{c.userName || 'Guest'}</div>
                        <div className="participant-status">Participant</div>
                      </div>
                      <div className="participant-controls">
                        {isMuted ? (
                          <FaMicrophoneSlash className="status-icon muted" />
                        ) : (
                          <FaMicrophone className="status-icon" />
                        )}
                        {isRaised && <FaHandPaper className="status-icon raised" />}
                        {!isStudent && (
                          <button
                            onClick={() => toggleMuteUser(c.userId, isMuted)}
                            className="mute-btn"
                          >
                            {isMuted ? 'Unmute' : 'Mute'}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
           
          </aside>
        )}
      </main>
 
       <footer className="bottom-controls">
              <div className="control-buttons">
                <button
                  onClick={toggleMic}
                  className={`control-btn mic ${currentMicId ? 'enabled' : 'disabled'}`}
                  title={micTitle}
                  disabled={user.role === 'student' && !currentMicId}
                >
                  {currentMicId ? <FaMicrophone /> : <FaMicrophoneSlash />}
                </button>
 
                <button
                  onClick={toggleCam}
                  className={`control-btn camera ${currentCameraId ? 'enabled' : 'disabled'}`}
                  title={currentCameraId ? 'Stop video' : 'Start video'}
                >
                  {currentCameraId ? <FaVideo /> : <FaVideoSlash />}
                </button>
                <button
                  onClick={toggleScreen}
                  className={`control-btn screen-share ${hasScreenShare ? 'active' : ''}`}
                  title={hasScreenShare ? 'Stop sharing' : 'Share screen'}
                >
                  {hasScreenShare ? <FaStop /> : <FaDesktop />}
                </button>
                <button
                  onClick={() => (isRecording ? stopRecording() : startRecording())}
                  className={`control-btn record ${isRecording ? 'active' : ''}`}
                  title={isRecording ? 'Stop recording' : 'Start recording'}
                  disabled={user.role !== 'teacher'}
                >
                  {isRecording ? <FaStopCircle /> : <FaCircle />}
                </button>
 
 
                {isStudent && (
                  <button
                    onClick={toggleHandRaise}
                    className={`control-btn hand-raise ${handRaised ? 'active' : ''}`}
                    title={handRaised ? 'Lower hand' : 'Raise hand'}
                  >
                    <FaHandPaper />
                  </button>
                )}
              </div>
              <button onClick={leaveMeeting} className="leave-meeting-btn" title="Leave meeting">
                <FaSignOutAlt />
                <span>Leave</span>
              </button>
            </footer>
           
    </div>
  )
}
 
function VideoBox({ id, stream, label, muted, flip = false, onPin, onDisconnect, pinned, sidebar, isMuted }) {
  const ref = useRef(null)
  const [hover, setHover] = useState(false)
  const [showInfo, setShowInfo] = useState(false)
  const [videoSize, setVideoSize] = useState({ width: 0, height: 0 })
  useEffect(() => {
    const el = ref.current
    if (!el) return
    if (el.srcObject !== stream) el.srcObject = stream
    const update = () => {
      const track = stream.getVideoTracks()[0]
      const s = track && track.getSettings ? track.getSettings() : {}
      setVideoSize({ width: s.width || 0, height: s.height || 0 })
    }
    update()
    const t = setInterval(update, 1000)
    return () => clearInterval(t)
  }, [stream])
  return (
    <div className={`video-box ${pinned ? 'pinned' : ''} ${sidebar ? 'sidebar' : ''}`} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      <video ref={ref} autoPlay playsInline muted={muted} className={`video-element ${flip ? 'flip' : ''}`} />
      {hover && (
        <div className="video-controls">
          {onPin && <button onClick={() => onPin(id)}>{pinned ? 'Unpin' : 'Pin'}</button>}
          <button onClick={() => setShowInfo(v => !v)}>Info</button>
          {onDisconnect && <button onClick={onDisconnect}>Disconnect</button>}
        </div>
      )}
      <div className="video-label">
        {isMuted && <FaMicrophoneSlash className="mute-icon" />}
        <span>{label}</span>
      </div>
      {showInfo && (
        <div className="video-info">
          <div>ID: {String(id)}</div>
          <div>Size: {videoSize.width}x{videoSize.height}</div>
          <div>Tracks: v{stream.getVideoTracks().length}/a{stream.getAudioTracks().length}</div>
        </div>
      )}
    </div>
  )
}
 
function disconnectByIdComposite(id) {
  const userId = String(id).split(':')[0]
  const st = useRemoteState.getState()
  const conn = st.connections.find(c => c.userId === userId)
  if (conn) destroyRemoteConnection(conn)
}
function disconnectById(id) { try { disconnectByIdComposite(id) } catch {} }