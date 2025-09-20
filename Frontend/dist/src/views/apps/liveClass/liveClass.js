import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
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
  FaPhoneSlash,
  FaHandPaper,
  FaClosedCaptioning,
  FaEllipsisV,
  FaInfoCircle,
  FaLock,
  FaTh,
  FaShare,
  FaTimes,
  FaVolumeUp,
  FaUserPlus,
  FaSignOutAlt
} from 'react-icons/fa'
import './LiveClass.css'

// Full meeting UI using only meetingSlice and external packages
export default function LiveClass() {
  const params = useParams()
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

  useEffect(() => {
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

  const toggleMic = async () => {
    const device = audioDevices.find(d => d.deviceId === currentMicId) || audioDevices[0] || dummyAudioDevice
    if (currentMicId) stopMediaDevice(device)
    else await startMediaDevice(device)
  }
  const toggleCam = async () => {
    const device = videoDevices.find(d => d.deviceId === currentCameraId) || videoDevices[0] || dummyVideoDevice
    if (currentCameraId) stopMediaDevice(device)
    else await startMediaDevice(device)
  }
  const toggleScreen = async () => { if (hasScreenShare) stopScreenCapture(); else await startScreenCapture() }

  const startRecording = async () => {
    try {
      const target = pinnedItem ? pinnedItem.stream : userStream
      if (!target) { toast('Nothing to record', { autoClose: Timeout.SHORT }); return }
      recordedBlobsRef.current = []
      const mr = new MediaRecorder(target, { mimeType: 'video/webm;codecs=vp9,opus' })
      mr.ondataavailable = e => { if (e.data && e.data.size > 0) recordedBlobsRef.current.push(e.data) }
      mr.onstop = () => {
        const blob = new Blob(recordedBlobsRef.current, { type: 'video/webm' })
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'recording.webm'; a.click(); URL.revokeObjectURL(a.href)
      }
      mr.start()
      recorderRef.current = mr
      setIsRecording(true)
      toast('Recording started', { autoClose: Timeout.SHORT })
    } catch { toast('Recording failed', { type: 'error' }) }
  }
  const stopRecording = () => {
    const mr = recorderRef.current
    if (mr && mr.state !== 'inactive') {
      mr.stop()
      recorderRef.current = null
      setIsRecording(false)
      toast('Recording saved', { autoClose: Timeout.SHORT })
    }
  }

  const leaveMeeting = () => {
    stopScreenCapture()
    audioDevices.forEach(stopMediaDevice)
    videoDevices.forEach(stopMediaDevice)
    connections.forEach(destroyRemoteConnection)
    if (socket) socket.close()
    window.history.back()
  }

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

  return (
    <div className="meet-container">
      {/* {hasAnyScreenShare && (
        <header className="presenting-header">
          <span>{presentingLabel}</span>
          <label className="presentation-audio">
            <input type="checkbox" checked={presentationAudio} onChange={() => setPresentationAudio(!presentationAudio)} />
            Presentation audio
          </label>
          <button onClick={toggleScreen} className="stop-presenting">Stop presenting</button>
          <button onClick={toggleFullscreen} className="fullscreen-btn" title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}>
            {isFullscreen ? <FaCompress /> : <FaExpand />}
          </button>
        </header>
      )} */}
        <header className="top-bar">
              <div className="meeting-info">
                <h1 className="meeting-title">Edu Pravaha</h1>
                <div className="meeting-meta">
                  <span className="meeting-time">{formatTime(meetingTime)}</span>
                  <span className="meeting-id">ID: {params.roomId || 'student'}</span>
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
                  </div>
                </div>
                {connections.map((c) => (
                  <div key={c.userId} className="participant-item">
                    <div className="participant-avatar">{(c.userName || 'Guest')[0].toUpperCase()}</div>
                    <div className="participant-info">
                      <div className="participant-name">{c.userName || 'Guest'}</div>
                      <div className="participant-status">Participant</div>
                    </div>
                    <div className="participant-controls">
                      {(remoteVideoItems.find((i) => i.id === c.userId)?.isMuted ? (
                        <FaMicrophoneSlash className="status-icon muted" />
                      ) : (
                        <FaMicrophone className="status-icon" />
                      ))}
                    </div>
                  </div>
                ))}
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
                  title={currentMicId ? 'Mute microphone' : 'Unmute microphone'}
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
                >
                  {isRecording ? <FaStopCircle /> : <FaCircle />}
                </button>
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