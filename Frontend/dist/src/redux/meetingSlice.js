import { useSyncExternalStore } from 'react'
import { io } from 'socket.io-client'
import Peer from 'simple-peer'
import adapter from 'webrtc-adapter'
import { nanoid } from 'nanoid'
import { toast as toastify, Slide } from 'react-toastify'
 
// ---------------------- Constants ----------------------
export const DOUBLE_CLICK_MS = 300
export const MIN_BANDWIDTH = 150 // kbps
export const MAX_BANDWIDTH = 2000 // kbps
export const ASPECT_RATIO = 16 / 9
export const VIDEO_RESOLUTION = 720
 
// ---------------------- Toast wrapper ----------------------
export const Timeout = { SHORT: 1500, MEDIUM: 3000, PERSIST: false }
export const ToastType = { info: 'info', success: 'success', warning: 'warning', error: 'error', blocked: 'error', severeWarning: 'warning' }
export const toastClasses = { container: undefined, body: undefined }
export default {}
export function toast(message, opts = {}) {
  const { type = ToastType.info, autoClose = Timeout.MEDIUM, body, onClick } = opts
  const content = body ? `${message}\n${body}` : message
  return toastify(content, { type, autoClose, onClick, transition: Slide, position: 'bottom-left', closeOnClick: false, closeButton: false, hideProgressBar: true, draggable: true })
}
export const dismissToast = toastify.dismiss
 
// ---------------------- Helpers ----------------------
const debugEnabled = typeof import.meta !== 'undefined' ? !!import.meta.env?.DEV : false
export function debug(...args) { if (debugEnabled) { try { console.debug('[mooz]', ...args) } catch {} } }
export function truncate(text, len) { if (!text) return ''; return text.length > len ? text.slice(0, len - 1) + '…' : text }
export function userLabel(x) { return x.userName || 'Anonymous' }
export function shallowEqual(a, b) {
  if (Object.is(a, b)) return true
  if (typeof a !== 'object' || a === null || typeof b !== 'object' || b === null) return false
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) if (!Object.is(a[i], b[i])) return false
    return true
  }
  const aKeys = Object.keys(a), bKeys = Object.keys(b)
  if (aKeys.length !== bKeys.length) return false
  for (let i = 0; i < aKeys.length; i++) { const k = aKeys[i]; if (!Object.prototype.hasOwnProperty.call(b, k) || !Object.is(a[k], b[k])) return false }
  return true
}
export function transformSdp(sdp, bandwidth /* kbps */) {
  try { return sdp.split('\n').map(line => (line.startsWith('m=video') ? `${line}\n b=AS:${bandwidth}` : line)).join('\n') } catch { return sdp }
}
 
// ---------------------- Stream class ----------------------
export class Stream extends MediaStream {
  addTrack(track) { super.addTrack(track); this.dispatchEvent(new MediaStreamTrackEvent('addtrack', { track })) }
  removeTrack(track) { track.stop(); super.removeTrack(track); this.dispatchEvent(new MediaStreamTrackEvent('removetrack', { track })) }
  destroy() { this.getTracks().forEach(t => this.removeTrack(t)) }
  get empty() { return this.getTracks().length === 0 }
  get noVideo() { return this.getVideoTracks().length === 0 }
  get noAudio() { return this.getAudioTracks().length === 0 }
}
 
// ---------------------- Tiny store (zustand-less) ----------------------
function create(initializer, options = {}) {
  const { persistKey, persistSelector } = options
  let state = initializer()
  if (typeof window !== 'undefined' && persistKey) {
    try { const raw = localStorage.getItem(persistKey); if (raw) state = { ...state, ...JSON.parse(raw) } } catch {}
  }
  const listeners = new Set()
  const getState = () => state
  const setState = update => {
    const partial = typeof update === 'function' ? update(state) : update
    const next = { ...state, ...partial }
    let changed = false
    for (const k in next) if (!Object.is(next[k], state[k])) { changed = true; break }
    if (!changed) return
    state = next
    if (typeof window !== 'undefined' && persistKey && typeof persistSelector === 'function') {
      try { localStorage.setItem(persistKey, JSON.stringify(persistSelector(state))) } catch {}
    }
    listeners.forEach(l => l())
  }
  const subscribe = listener => { listeners.add(listener); return () => listeners.delete(listener) }
  function useStore(selector = s => s, equalityFn = shallowEqual) {
    const snapshot = useSyncExternalStore(subscribe, getState)
    const selected = selector(snapshot)
    const cache = (useStore.__cache ||= new WeakMap())
    let prev = cache.get(selector)
    if (prev === undefined) { cache.set(selector, selected); prev = selected }
    else if (!equalityFn(prev, selected)) { cache.set(selector, selected); prev = selected }
    return prev
  }
  useStore.getState = getState
  useStore.setState = setState
  useStore.subscribe = subscribe
  return useStore
}
 
// ---------------------- Local state ----------------------
function getSessionId() { const id = sessionStorage.getItem('ID') || nanoid(); sessionStorage.setItem('ID', id); return id }
export const useLocalState = create(
  () => ({
    sessionId: getSessionId(),
    userStream: new Stream(),
    displayStream: new Stream(),
    audioDevices: [],
    videoDevices: [],
    currentMicId: null,
    currentCameraId: null,
    screenMediaActive: false,
    inviteCoachmarkVisible: true,
    showEmptyMediaPanel: true,
    sidePanelTab: undefined,
    floatingChatEnabled: false,
    fullscreenEnabled: false,
    preferences: {},
  }),
  { persistKey: 'mooz-prefs', persistSelector: state => ({ preferences: state.preferences }) },
)
export async function updateDevicesList() {
  if (!navigator.mediaDevices.ondevicechange) navigator.mediaDevices.ondevicechange = updateDevicesList
  const devices = await navigator.mediaDevices.enumerateDevices()
  useLocalState.setState({
    audioDevices: devices.filter(d => d.kind === 'audioinput'),
    videoDevices: devices.filter(d => d.kind === 'videoinput'),
  })
}
export function updateActiveMediaSources() {
  const stream = useLocalState.getState().userStream
  const currentMicId = stream.getAudioTracks()[0]?.getSettings?.()?.deviceId || null
  const currentCameraId = stream.getVideoTracks()[0]?.getSettings?.()?.deviceId || null
  useLocalState.setState({ currentMicId, currentCameraId })
}
export function updateActiveDiplayStatus() {
  const stream = useLocalState.getState().displayStream
  useLocalState.setState({ screenMediaActive: !stream.empty })
}
const commonDummyDevice = { toJSON: () => ({}), deviceId: '', label: '', groupId: '' }
export const dummyAudioDevice = { ...commonDummyDevice, kind: 'audioinput' }
export const dummyVideoDevice = { ...commonDummyDevice, kind: 'videoinput' }
export function stopMediaDevice(device) {
  const stream = useLocalState.getState().userStream
  stream.getTracks().forEach(track => {
    if (device.kind.startsWith(track.kind) && track.getSettings().deviceId === device.deviceId) {
      stream.removeTrack(track)
    }
  })
  updateActiveMediaSources()
}
export async function startMediaDevice(device) {
  try {
    const config = {
      audio: { deviceId: device.deviceId, echoCancellation: true, noiseSuppression: true },
      video: { deviceId: device.deviceId, height: { ideal: VIDEO_RESOLUTION }, aspectRatio: ASPECT_RATIO, noiseSuppression: true },
    }
    const stream = useLocalState.getState().userStream
    if (device.kind === 'audioinput') { if (stream.getAudioTracks().length) throw Error('Audio already active'); config.video = false }
    else if (device.kind === 'videoinput') { if (stream.getVideoTracks().length) throw Error('Video already active'); config.audio = false }
    ;(await navigator.mediaDevices.getUserMedia(config)).getTracks().forEach(track => { track.onended = () => stopMediaDevice(device); stream.addTrack(track) })
    updateDevicesList(); updateActiveMediaSources()
  } catch (error) {
    const body = error instanceof Error ? error.message : 'Unknown error'
    toast('Cannot start media feed.', { type: ToastType.blocked, body })
    console.error(error)
  }
}
export function stopScreenCapture() {
  const stream = useLocalState.getState().displayStream
  stream.getTracks().forEach(track => stream.removeTrack(track))
  updateActiveDiplayStatus()
}
export async function startScreenCapture() {
  try {
    const stream = useLocalState.getState().displayStream
    if (stream.getTracks().length) throw Error('Screen capture already active')
    ;(await navigator.mediaDevices.getDisplayMedia({ video: { cursor: 'always' }, audio: { echoCancellation: true, noiseSuppression: true } }))
      .getTracks()
      .forEach(track => { track.onended = () => stopScreenCapture(); stream.addTrack(track) })
    updateActiveDiplayStatus()
  } catch (err) {
    const body = err instanceof Error ? err.message : 'Unknown error'
    toast('Cannot start screen capture.', { type: ToastType.blocked, body })
    console.error(err)
  }
}
const enterRoomSound = { src: '/sounds/enter-room.mp3', volume: 0.2 }
const leaveRoomSound = { src: '/sounds/abort-room.mp3', volume: 0.1 }
const chatReceivedSound = { src: '/sounds/chat-received.mp3', volume: 0.3 }
const audioEl = typeof Audio !== 'undefined' ? new Audio() : null
if (audioEl) { const onClick = () => { audioEl.play().catch(() => {}); window.removeEventListener('click', onClick) }; window.addEventListener('click', onClick) }
export function playEnterRoomSound() { if (!audioEl) return; audioEl.src = enterRoomSound.src; audioEl.volume = enterRoomSound.volume; audioEl.play() }
export function playLeaveRoomSound() { if (!audioEl) return; audioEl.src = leaveRoomSound.src; audioEl.volume = leaveRoomSound.volume; audioEl.play() }
export function playChatReceivedSound() { if (!audioEl) return; audioEl.src = chatReceivedSound.src; audioEl.volume = chatReceivedSound.volume; audioEl.play() }
 
// ---------------------- Chat state ----------------------
export const useChatState = create(() => ({ messages: [] }))
export function onChatReceived(chat) {
  const local = useLocalState.getState()
  const isInChats = local.sidePanelTab === 'chats' || local.floatingChatEnabled
  if (!isInChats) {
    toast(`${chat.userLabel} sent a message: ${truncate(chat.text, 45)}`, {
      type: ToastType.info,
      autoClose: Timeout.MEDIUM,
      body: 'Click to open chats',
      onClick: () => useLocalState.setState({ sidePanelTab: 'chats' }),
    })
  }
  playChatReceivedSound()
  useChatState.setState(s => ({ messages: [...s.messages, { ...chat, mine: false }] }))
}
export function sendChat(chat) {
  useChatState.setState(s => ({ messages: [...s.messages, { ...chat, mine: true }] }))
  const connections = useRemoteState.getState().connections
  connections.map(c => c.peerInstance).filter(Boolean).forEach(peer => {
    try { peer.send(JSON.stringify({ chat: { ...chat, mine: false } })) }
    catch (err) {
      toast('Message could not be sent, try again', { type: ToastType.error })
      useChatState.setState(s => ({ messages: s.messages.filter(m => m.id !== chat.id) }))
    }
  })
}
 
// ---------------------- Landing form state ----------------------
export const useCreateFormState = create(() => ({ capacity: '10', userName: '', meetingName: 'Mooz Meeting', loading: false, error: null }))
export const useJoinFormState = create(() => ({ userName: '', roomId: '', loading: false, error: null }))
export function getLandingDefaults() { const hash = window.location.hash; if (hash.includes('join')) return { key: 'join' }; return { key: 'create' } }
 
// ---------------------- Remote (socket/rtc) state ----------------------
export function createSocket() {
  const env = (typeof import.meta !== 'undefined' && import.meta.env) || {}
  const sameOriginUrl = '' // same-origin by default (proxy/dev-server)
  const socket = io('http://localhost:8000', {
    path: '/socket.io/',
    transports: ['websocket'],
    auth: (cb) => {
      const { sessionId } = useLocalState.getState();
      const { id: currentRoomId } = useRemoteState.getState().room || {};
      // Retrieve bearer token and user_type (e.g., from localStorage or auth context)
      const token = localStorage.getItem('access') || ''; // Replace with your token storage mechanism
      const rawUserData = localStorage.getItem('userData');
      const userData = rawUserData ? JSON.parse(rawUserData) : null;
      const userRole = userData?.role || null;
      console.log('createSocket auth:', { sessionId, currentRoomId, token,  userRole});

      cb({ sessionId, currentRoomId, token, userRole });
    },
  });
  socket.onAny((event, ...args) => debug(`socket.io: '${event}'`, ...args))

  // Handle connection errors
  socket.on('connect_error', (error) => {
    const message = error.message || 'Connection failed';
    toast(message, { type: ToastType.error, autoClose: Timeout.MEDIUM });
    debug(`socket.io: connect_error`, error);
    console.error('Socket connection error:', error); // <-- added console
  });
 
  // Optional: catch general errors
  socket.on('error', (error) => {
    console.error('Socket error event:', error);
  });
  return socket
}
 
export const useRemoteState = create(() => ({ socket: createSocket(), room: null, connections: [] }))
 
export function setupLocalMediaListeners() {
  const { userStream, displayStream } = useLocalState.getState()
  userStream.addEventListener('addtrack', ({ track }) => {
    const { connections } = useRemoteState.getState()
    connections.forEach(conn => { conn.peerInstance.addTrack(track, conn.userStream) })
  })
  userStream.addEventListener('removetrack', ({ track }) => {
    const { connections } = useRemoteState.getState()
    connections.forEach(conn => { conn.peerInstance.removeTrack(track, conn.userStream) })
  })
  displayStream.addEventListener('addtrack', ({ track }) => {
    const { connections } = useRemoteState.getState()
    connections.forEach(conn => { conn.peerInstance.addTrack(track, conn.displayStream) })
  })
  displayStream.addEventListener('removetrack', ({ track }) => {
    const { connections } = useRemoteState.getState()
    connections.forEach(conn => { conn.peerInstance.removeTrack(track, conn.displayStream) })
  })
}
 
export function createPeerInstance(opts) {
  return new Peer({
    sdpTransform: function (sdp) {
      const { connections } = useRemoteState.getState()
      const bandwidth = Math.max((MAX_BANDWIDTH / (connections.length || 1)) >>> 0, MIN_BANDWIDTH)
      if (
        (adapter.browserDetails.browser === 'chrome' ||
          adapter.browserDetails.browser === 'safari' ||
          (adapter.browserDetails.browser === 'firefox' && adapter.browserDetails.version && adapter.browserDetails.version >= 64)) &&
        'RTCRtpSender' in window && 'setParameters' in window.RTCRtpSender.prototype
      ) {
        connections.forEach(({ peerInstance }) => {
          const sender = peerInstance?._pc?.getSenders?.()[0]
          if (!sender) return
          const parameters = sender.getParameters()
          if (!parameters.encodings || !parameters.encodings.length) return
          const encoding = parameters.encodings[0]
          if (encoding.maxBitrate !== bandwidth * 1000) { encoding.maxBitrate = bandwidth * 1000; sender.setParameters(parameters) }
        })
        return sdp
      }
      return transformSdp(sdp, bandwidth, this)
    },
    ...opts,
  })
}
 
export function createRemoteConnection({ initiator, userId, userName }) {
  if (!Peer.WEBRTC_SUPPORT) { alert('Your browser does not support WebRTC or it is disabled.'); return }
  const state = useRemoteState.getState()
  if (state.connections.find(c => c.userId === userId)) {
    // duplicate — ignore
    return
  }
  const { socket } = state
  const roomId = useRemoteState.getState().room?.id
  const localState = useLocalState.getState()
  const { userName: nameSelf } = localState.preferences
  const { userStream, displayStream } = localState
 
  const peer = createPeerInstance({ initiator })
  const connection = { userId, userName, peerInstance: peer, userStream: new Stream(), displayStream: new Stream(), initiator }
  const reRenderConnection = () =>
    useRemoteState.setState(state => ({
      connections: state.connections.map(c => (c.userId === userId ? { ...c } : c)),
    }))
 
  userStream.getTracks().forEach(track => peer.addTrack(track, connection.userStream))
  displayStream.getTracks().forEach(track => peer.addTrack(track, connection.displayStream))
 
  peer.on('signal', sdpSignal => {
    state.socket.emit('request:send_mesage', {
      to: userId,
      roomId,
      data: {
        sdpSignal,
        metaData: { screenStreamId: connection.displayStream.id, userStreamId: connection.userStream.id },
      },
    })
  })
  peer.on('error', err => {
    toast('Peer connection error', { type: ToastType.blocked, body: err.message, autoClose: Timeout.MEDIUM })
    console.error(err)
    socket.emit('request:leave_room', { roomId })
  })
  peer.on('close', () => {
    toast('Peer connection closed with ' + userLabel(connection), { type: ToastType.severeWarning, autoClose: Timeout.SHORT })
  })
  peer.on('connect', () => {
    toast('Peer connection established with ' + userLabel(connection), { type: ToastType.success, autoClose: Timeout.SHORT })
  })
  peer.on('data', str => {
    try {
      const data = JSON.parse(str)
      if (data.chat) onChatReceived(data.chat)
    } catch {}
  })
  peer.on('track', (track, stream) => {
    const metaData = useRemoteState.getState().connections.find(c => c.userId === connection.userId)?.metaData
    const streamType = stream.id === metaData?.screenStreamId ? 'displayStream' : 'userStream'
    connection[streamType].addTrack(track)
    reRenderConnection()
    stream.onremovetrack = ({ track }) => {
      connection[streamType].removeTrack(track)
      reRenderConnection()
    }
  })
 
  if (!initiator) {
    socket.emit('request:send_mesage', {
      to: userId,
      roomId,
      data: { connection: true, userName: nameSelf || '' },
    })
  }
  useRemoteState.setState(state => ({ connections: [...state.connections, connection] }))
}
 
export function destroyRemoteConnection(connection) {
  useRemoteState.setState(state => ({ connections: state.connections.filter(c => c.userId !== connection.userId) }))
  connection.userStream.destroy()
  connection.displayStream.destroy()
  connection.peerInstance.destroy()
}
 
 
export function requestLeaveRoom() {
  const { sessionId } = useLocalState.getState()
  const { room } = useRemoteState.getState()
  console.log('[mooz] requestLeaveRoom → roomId:', room?.id, 'sessionId:', sessionId)
 
  useRemoteState.setState(state => {
    const { socket, room } = state
    if (!room) return {}
    socket.emit('request:leave_room', { roomId: room.id,sessionId }, error => { if (error) toast(error.message, { type: ToastType.error }) })
    return {}
  })
}
 
export function enterRoom(room) {
  console.log('[mooz] enterRoom → roomId:', room.id, 'sessionId:', useLocalState.getState().sessionId)
  useRemoteState.setState({ room })
  playEnterRoomSound()
  window.history.pushState({}, 'Mooz', `/room/${room.id}`)
  toast(`Joined ${room.name}`)
  useJoinFormState.setState({ roomId: room.id })
}
 
export function abortRoom() {
  useRemoteState.setState(state => {
    state.connections.forEach(connection => destroyRemoteConnection(connection))
    return { room: null }
  })
  toast('Room aborted!, enjoy your lonely life', { type: ToastType.warning })
  playLeaveRoomSound()
  useLocalState.setState({ showEmptyMediaPanel: true })
}
 
// ---------------------- Attach socket listeners globally (CRITICAL) ----------------------
;(function attachSocketHandlersOnce() {
  const socket = useRemoteState.getState().socket
  if (!socket || socket.__moozHandlersAttached) return
  socket.__moozHandlersAttached = true
 
  try { setupLocalMediaListeners() } catch {}
 
  socket.on('action:establish_peer_connection', ({ userId, userName }) => {
    try { createRemoteConnection({ userId, userName, initiator: false }) } catch {}
  })
 
  socket.on('action:message_received', ({ from, data }) => {
    const connections = useRemoteState.getState().connections
    if (data && data.connection) {
      try { createRemoteConnection({ userId: from, initiator: true, userName: data.userName || '' }) } catch {}
      return
    }
    if (data && 'sdpSignal' in data) {
      const conn = connections.find(c => c.userId === from)
      if (!conn) return
      try { conn.metaData = data.metaData; conn.peerInstance.signal(data.sdpSignal) } catch (err) { console.error('sdp signal error:', err) }
    }
  })
 
  socket.on('action:terminate_peer_connection', ({ userId }) => {
    const connections = useRemoteState.getState().connections
    const conn = connections.find(c => c.userId === userId)
    if (!conn) return
    toast(`${conn?.userName} left the meeting`, { autoClose: Timeout.SHORT })
    destroyRemoteConnection(conn)
  })
})()