  import React, { useEffect, useRef, useState } from "react";
  import { FaPlay, FaPause, FaVolumeUp, FaVolumeMute, FaExpand } from "react-icons/fa";
  import { useDispatch, useSelector } from "react-redux";
  import { fetchRecordedVideos } from "../../../redux/recordedVideosSlice";
  import { Spinner } from "reactstrap";
  import '@styles/react/pages/RecordedClasses.scss'
import SpinnerComponent from "../../../@core/components/spinner/Fallback-spinner";
import ComponentSpinner from "../../../@core/components/spinner/Loading-spinner";

  const RecordedClasses = () => {
    const [selectedCourse, setSelectedCourse] = useState(null);
    const { courses, courseRecordings, loading } = useSelector((state) => state.recordedVideos);
    const videoRefs = useRef({});
    const dispatch = useDispatch();

    // Fetch course list on mount
    useEffect(() => {
      dispatch(fetchRecordedVideos());
    }, [dispatch]);

    // Handle course click → fetch its recordings
    const handleCourseClick = (course) => {
      setSelectedCourse(course);
      dispatch(fetchRecordedVideos(course.course_id));
    };

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
        
              {/* {loading && (
              <div
                className="d-flex justify-content-center align-items-center"
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  background: "transparent  overlay", 
                  zIndex: 9999,
                }}
              >
                <Spinner style={{ width: "3rem", height: "3rem" }} color="primary" />
              </div>
            )} */}
            {loading && (
      <ComponentSpinner/>
    )}
     {/* {loading && <SpinnerComponent />} */}

        {/* Show course list */}
        {!selectedCourse ? (
          <div className="courses-grid">
            {courses.map((course) => (
              <div
                key={course.course_id}
                className="course-card"
                onClick={() => handleCourseClick(course)}
              >
                <div className="course-thumb">
                  <img
                    src={course.thumbnail || "https://media.istockphoto.com/id/1353769234/photo/training-and-skill-development-concept-with-icons-of-online-course-conference-seminar-webinar.jpg?s=612x612&w=0&k=20&c=2YJG1My6Lu1T1FnzIPbimRNORcSbSuz6A8zb7HKNpx4="}
                    alt={course.course_name}
                  />
                </div>
                <div className="course-info">
                  <h3 className="course-title">{course.course_name}</h3>
                  <div className="course-meta">
                    {course.recording_count} video
                    {course.recording_count !== 1 ? "s" : ""}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          // Show recordings of selected course
          <div className="videos-section">
            <button className="back-btn" onClick={() => {
              setSelectedCourse(null);
            }}>
              ← Back to Courses
            </button>

            {/* Header */}
            <div className="course-header">
              <div className="course-header-left">
                <img
                  className="course-header-thumb"
                  src={selectedCourse.thumbnail || "https://media.istockphoto.com/id/1353769234/photo/training-and-skill-development-concept-with-icons-of-online-course-conference-seminar-webinar.jpg?s=612x612&w=0&k=20&c=2YJG1My6Lu1T1FnzIPbimRNORcSbSuz6A8zb7HKNpx4="
          }
                  alt={selectedCourse.course_name}
                />
              </div>
              <div className="course-header-right">
                <h2 className="course-header-title">{selectedCourse.course_name}</h2>
                <div className="course-header-meta">
                  {courseRecordings[0]?.recording_count || 0} video
                  {(courseRecordings[0]?.recording_count || 0) !== 1 ? "s" : ""}
                </div>
                <p className="course-batch">
                  Batch: {courseRecordings[0]?.batch_name} (
                  {courseRecordings[0]?.batch_start_date} →{" "}
                  {courseRecordings[0]?.batch_end_date})
                </p>
              </div>
            </div>

            {/* Videos Grid */}
            <div className="videos-grid">
              {courseRecordings[0]?.batch_recordings?.map((video,index) => {
                const refKey = `${selectedCourse.course_id}:${video.class_id}`;
                return (
                  <VideoCard
                    key={video.class_id}
                    title={`${selectedCourse.course_name} class ${index + 1}`}
                    src={video.recording}
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

  // ⏱️ Format time
  function formatTime(seconds) {
    if (Number.isNaN(seconds) || seconds === Infinity) return "0:00";
    const s = Math.floor(seconds % 60).toString().padStart(2, "0");
    const m = Math.floor((seconds / 60) % 60).toString();
    const h = Math.floor(seconds / 3600);
    return h > 0 ? `${h}:${m.padStart(2, "0")}:${s}` : `${m}:${s}`;
  }

  // 🎬 Video card
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
      if (v.paused) {
        v.play();
        setIsPlaying(true);
      } else {
        v.pause();
        setIsPlaying(false);
      }
    };

    const toggleMute = () => {
      const v = videoRefs.current[refKey];
      if (!v) return;
      v.muted = !v.muted;
      setIsMuted(v.muted);
    };

const onSeek = (e) => {
  const v = videoRefs.current[refKey];
  if (!v || !progressRef.current) return;

  const updateSeek = (clientX) => {
    const rect = progressRef.current.getBoundingClientRect();
    const ratio = Math.min(Math.max(0, (clientX - rect.left) / rect.width), 1);
    const t = ratio * (v.duration || 0);
    v.currentTime = t;
    setCurrent(t);
  };

  // Start seeking on mouse down
  updateSeek(e.clientX);

  const onMove = (moveEvent) => updateSeek(moveEvent.clientX);
  const onUp = () => {
    document.removeEventListener("mousemove", onMove);
    document.removeEventListener("mouseup", onUp);
  };

  document.addEventListener("mousemove", onMove);
  document.addEventListener("mouseup", onUp);
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
            controls={false}
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
          <div className="progress-bar" ref={progressRef} onMouseDown={onSeek}   >
            <div
              className="progress-fill"
              style={{ width: `${duration ? (current / duration) * 100 : 0}%` }}
            />
          </div>
        </div>
        <h4 className="video-title">{title}</h4>
      </div>
    );
  }

  export default RecordedClasses;
