import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  Stack,
  Pivot,
  PivotItem,
  TextField,
  SpinButton,
  Label,
  PrimaryButton,
  Toggle,
  useTheme,
  Persona,
  IconButton,
  

} from '@fluentui/react'
import { 
  FaMicrophone, 
  FaMicrophoneSlash, 
  FaVideo, 
  FaVideoSlash   
} from 'react-icons/fa'
import fscreen from 'fscreen'
import {
  getLandingDefaults,
  useCreateFormState,
  useJoinFormState,
  useLocalState,
  useRemoteState,
  dummyAudioDevice,
  dummyVideoDevice,
  startMediaDevice,
  stopMediaDevice,
} from '../../../redux/meetingSlice'
import './index.css'

const pivotStyles = { itemContainer: { padding: '.5em', width: '300px', height: '225px' } }

function VideoPreview() {
  const [mediaBtnsDisabled, setMediaBtnsDisabled] = useState(false)
  const [userStream, currentCameraId, currentMicId, audioDevices, videoDevices, preferences] =
    useLocalState(state => [state.userStream, state.currentCameraId, state.currentMicId, state.audioDevices, state.videoDevices, state.preferences])

  const audioDevice = audioDevices.find(d => d.deviceId === currentMicId)
  const videoDevice = videoDevices.find(d => d.deviceId === currentCameraId)
  const mediaInfo = [videoDevice?.label, audioDevice?.label].filter(Boolean).join('\n').trim()

  return (
    <div className="prejoin-card">
      <div className="prejoin-header">
        <div className="google-meet-logo">Live Meet</div>
        <div className="meeting-info"><p>Do you want people to see and hear you in the meeting?</p></div>
      </div>
      <div className="video-preview">
        <video
          className="preview-video"
          playsInline
          muted
          autoPlay
          style={{ transform: 'scaleX(-1)' }}
          ref={el => { if (el && userStream && el.srcObject !== userStream) el.srcObject = userStream }}
        />
        <div className="meet-controls">
           <button
            className={`circle-btn ${currentMicId ? '' : 'danger'}`}
            onClick={async () => {
          setMediaBtnsDisabled(true)
              if (currentMicId) stopMediaDevice(audioDevices[0] || dummyAudioDevice)
              else await startMediaDevice(audioDevices[0] || dummyAudioDevice)
          setMediaBtnsDisabled(false)
            }}
            disabled={mediaBtnsDisabled}
          >
            {currentMicId ? <FaMicrophone /> : <FaMicrophoneSlash />}
          </button>
           <button
            className={`circle-btn ${currentCameraId ? '' : 'danger'}`}
            onClick={async () => {
          setMediaBtnsDisabled(true)
              if (currentCameraId) stopMediaDevice(videoDevices[0] || dummyVideoDevice)
              else await startMediaDevice(videoDevices[0] || dummyVideoDevice)
          setMediaBtnsDisabled(false)
            }}
            disabled={mediaBtnsDisabled}
          >
            {currentCameraId ? <FaVideo /> : <FaVideoSlash />}
          </button>
        </div>
      </div>
      {/* Below toggles removed per Meet UI — using only circular icon buttons on video */}
      {/* <div style={{ color: '#666', fontSize: 12, whiteSpace: 'pre-line', textAlign: 'center' }}>{mediaInfo}</div> */}
        </div>
  )
}

// function CreateMeeting() {
//   const navigate = useNavigate()
//   const [userNameError, setUserNameError] = useState('')
//   const preferences = useLocalState(state => state.preferences)
//   const socket = useRemoteState(state => state.socket)
//   const { capacity, meetingName, userName, loading, error } = useCreateFormState()
//   const setState = useCreateFormState.setState
//   const theme = useTheme()
//
//   const handleSubmit = useCallback(e => {
//     e.preventDefault()
//     if (!userName.trim()) { setUserNameError('Please enter your name'); return }
//     if (loading) return
//     setState({ error: null, loading: true })
//     const room = { id: '', name: meetingName, created_by: userName, opts: { capacity: parseInt(capacity) || 0 } }
//     const onEstablished = ({ room }) => {
//       try { if (room && room.id) navigate(`/live-class/session/${room.id}`) }
//       finally { socket.off('action:room_connection_established', onEstablished) }
//     }
//     socket.once('action:room_connection_established', onEstablished)
//     socket.emit('request:create_room', { room }, err => {
//       if (err) setState({ error: err.message })
//       setState({ loading: false })
//     })
//     useLocalState.setState({ preferences: { ...preferences, userName, meetingName } })
//   }, [loading, capacity, meetingName, userName, preferences, socket, navigate, setState])
//
//   return (
//     <Stack>
//       <form onSubmit={handleSubmit}>
//         <SpinButton styles={{ root: { marginBottom: 10 } }} value={capacity.toString()} onChange={(_, v = '1') => setState({ capacity: v })} label="Maximum number of participants" min={1} max={50} step={1} />
//         <TextField styles={{ root: { marginBottom: 10 } }} value={userName} onChange={(_, v = '') => { setState({ userName: v }); if (userNameError) setUserNameError('') }} placeholder="Your name" errorMessage={userNameError} required />
//         <TextField value={meetingName} onChange={(_, v = '') => setState({ meetingName: v })} placeholder="Meeting name" />
//         <Label style={{ color: theme.palette.red }}>{error}</Label>
//         <Stack.Item><PrimaryButton disabled={loading} checked={loading} type="submit" styles={{ root: { marginTop: 10 } }}>{loading ? 'Creating…' : 'Create'}</PrimaryButton></Stack.Item>
//       </form>
//     </Stack>
//   )
// }

function JoinMeeting() {
  const navigate = useNavigate()
  const [userNameError, setUserNameError] = useState('')
  const theme = useTheme()
  const socket = useRemoteState(state => state.socket)
  const preferences = useLocalState(state => state.preferences)
  const { loading, error, userName, roomId } = useJoinFormState()
  const setState = useJoinFormState.setState
  const params = useParams()

  useEffect(() => { const preset = params?.roomId; if (preset) setState({ roomId: preset }) }, [params, setState])

  const handleSubmit = useCallback(e => {
    e.preventDefault()
    if (!userName.trim()) { setUserNameError('Please enter your name'); return }
    if (loading) return
    setState({ loading: true, error: null })
    socket.emit('request:join_room', { userName, roomId }, err => {
      if (err) setState({ error: err.message })
      setState({ loading: false })
      if (!err) navigate(`/live-class/session/${roomId}`)
    })
    useLocalState.setState({ preferences: { ...preferences, userName } })
  }, [loading, preferences, roomId, userName, socket, navigate, setState])

  return (
    <Stack>
      <form onSubmit={handleSubmit}>
        {/* Hidden room id field for functionality retained */}
        {/* <TextField styles={{ root: { marginBottom: 10 } }} value={roomId} onChange={(_, v = '') => setState({ roomId: v })} label="Meeting link or id" required /> */}
        <TextField value={userName} onChange={(_, v = '') => { setState({ userName: v }); if (userNameError) setUserNameError('') }} placeholder="Your name" errorMessage={userNameError} 
        className='custom-class' />
        <Label style={{ color: theme.palette.red }}>{error}</Label>
        <PrimaryButton type="submit" styles={{ root: { marginTop: 10, width: '100%' } }}>{loading ? 'Joining…' : 'Join now'}</PrimaryButton>
      </form>
    </Stack>
  )
}

export default function Landing() {
  const params = useParams()
  useEffect(() => { if (fscreen.fullscreenElement) fscreen.exitFullscreen() }, [])
  return (
    <div className="prejoin-container">
      <VideoPreview />
      <div className="join-form-card">
        <div className="ready-title">Ready to join?</div>
        <JoinMeeting />
      </div>
    </div>
  )
}