import React, { useEffect, useMemo, useRef, useState } from "react";
import { FaPlay, FaPause, FaVolumeUp, FaVolumeMute, FaExpand } from "react-icons/fa";
import "./RecordedClasses.css";

const RecordedClasses = () => {
  const [selectedCourse, setSelectedCourse] = useState(null);
  const videoRefs = useRef({});

  const courses = [
    {
      id: 1,
      title: "React Basics",
      image: "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?w=800&q=80&auto=format&fit=crop",
      videos: [
        { id: 101, title: "Introduction to React", url: "https://www.w3schools.com/html/mov_bbb.mp4" },
        { id: 102, title: "Components and Props", url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4" },
      ],
    },
    {
      id: 2,
      title: "Django Backend",
      image: "https://images.unsplash.com/photo-1587620962725-abab7fe55159?w=800&q=80&auto=format&fit=crop",
      videos: [
        { id: 201, title: "Getting Started", url: "https://www.w3schools.com/html/mov_bbb.mp4" },
        { id: 202, title: "Django Models", url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4" },
      ],
    },
    {
      id: 3,
      title: "Data Structures",
      image: "https://images.unsplash.com/photo-1518779578993-ec3579fee39f?w=800&q=80&auto=format&fit=crop",
      videos: [
        { id: 301, title: "Arrays & Linked Lists", url: "https://www.w3schools.com/html/mov_bbb.mp4" },
        { id: 302, title: "Stacks & Queues", url: "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4" },
      ],
    },
  ];

  const handleFullScreen = (key) => {
    const el = videoRefs.current[key];
    if (!el) return;
    if (el.requestFullscreen) {
      el.requestFullscreen();
    } else if (el.webkitRequestFullscreen) {
      el.webkitRequestFullscreen();
    } else if (el.msRequestFullscreen) {
      el.msRequestFullscreen();
    }
  };

  return (
    <div className="recorded-container">
      {!selectedCourse ? (
        <div className="courses-grid">
          {courses.map((course) => (
            <div key={course.id} className="course-card" onClick={() => setSelectedCourse(course)}>
              <div className="course-thumb">
                <img src={course.image} alt={course.title} />
              </div>
              <div className="course-info">
                <h3 className="course-title">{course.title}</h3>
                <div className="course-meta">{course.videos.length} video{course.videos.length !== 1 ? "s" : ""}</div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="videos-section">
          <button className="back-btn" onClick={() => setSelectedCourse(null)}>
            ← Back to Courses
          </button>
          <div className="course-header">
            <div className="course-header-left">
              <img className="course-header-thumb" src={selectedCourse.image} alt={selectedCourse.title} />
            </div>
            <div className="course-header-right">
              <h2 className="course-header-title">{selectedCourse.title}</h2>
              <div className="course-header-meta">{selectedCourse.videos.length} video{selectedCourse.videos.length !== 1 ? "s" : ""}</div>
            </div>
          </div>
          <div className="videos-grid">
            {selectedCourse.videos.map((video) => {
              const refKey = `${selectedCourse.id}:${video.id}`;
              return (
                <VideoCard
                  key={video.id}
                  title={video.title}
                  src={video.url}
                  refKey={refKey}
                  videoRefs={videoRefs}
                  onFullscreen={() => handleFullScreen(refKey)}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

function formatTime(seconds) {
  if (Number.isNaN(seconds) || seconds === Infinity) return "0:00";
  const s = Math.floor(seconds % 60).toString().padStart(2, "0");
  const m = Math.floor((seconds / 60) % 60).toString();
  const h = Math.floor(seconds / 3600);
  return h > 0 ? `${h}:${m.padStart(2, "0")}:${s}` : `${m}:${s}`;
}

function VideoCard({ title, src, refKey, videoRefs, onFullscreen }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [duration, setDuration] = useState(0);
  const [current, setCurrent] = useState(0);
  const progressRef = useRef(null);

  const onLoadedMetadata = () => {
    const v = videoRefs.current[refKey];
    if (!v) return;
    setDuration(v.duration || 0);
  };

  const onTimeUpdate = () => {
    const v = videoRefs.current[refKey];
    if (!v) return;
    setCurrent(v.currentTime || 0);
  };

  const togglePlay = () => {
    const v = videoRefs.current[refKey];
    if (!v) return;
    if (v.paused) { v.play(); setIsPlaying(true); } else { v.pause(); setIsPlaying(false); }
  };

  const toggleMute = () => {
    const v = videoRefs.current[refKey];
    if (!v) return;
    v.muted = !v.muted;
    setIsMuted(v.muted);
  };

  const onSeek = (e) => {
    const v = videoRefs.current[refKey];
    if (!v) return;
    const rect = progressRef.current.getBoundingClientRect();
    const ratio = Math.min(Math.max(0, (e.clientX - rect.left) / rect.width), 1);
    const t = ratio * (v.duration || 0);
    v.currentTime = t;
    setCurrent(t);
  };

  return (
    <div className="video-card">
      <div className="video-wrapper">
        <video
          ref={(node) => (videoRefs.current[refKey] = node)}
          className="video-player"
          onLoadedMetadata={onLoadedMetadata}
          onTimeUpdate={onTimeUpdate}
          src={src}
        />
        <div className="video-overlay-controls">
          <button className="control-btn" onClick={togglePlay} aria-label={isPlaying ? "Pause" : "Play"}>
            {isPlaying ? <FaPause /> : <FaPlay />}
          </button>
          <button className="control-btn" onClick={toggleMute} aria-label={isMuted ? "Unmute" : "Mute"}>
            {isMuted ? <FaVolumeMute /> : <FaVolumeUp />}
          </button>
          <div className="time-display">
            {formatTime(current)} / {formatTime(duration)}
          </div>
          <button className="control-btn" onClick={onFullscreen} aria-label="Fullscreen">
            <FaExpand />
          </button>
        </div>
        <div className="progress-bar" ref={progressRef} onClick={onSeek}>
          <div className="progress-fill" style={{ width: `${duration ? (current / duration) * 100 : 0}%` }} />
        </div>
      </div>
      <h4 className="video-title">{title}</h4>
    </div>
  );
}

export default RecordedClasses;