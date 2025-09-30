import React, { useEffect } from "react";
import { Clock, BookOpen, CheckCircle } from "react-feather";
import { useDispatch, useSelector } from "react-redux";
import { fetchDashboardData } from "../../../redux/studentDashboardSlice";
import "@styles/react/pages/student-dashboard.scss"; // ✅ SCSS import

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from "recharts";
import { Spinner } from "reactstrap";
import MyCourses from "../../apps/mycourses";

// ✅ Custom Tooltip (white in light theme, dark stays same)
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const isDarkMode = document.body.classList.contains("dark-layout");

    return (
      <div
        style={{
          backgroundColor: isDarkMode ? "#1f2937" : "#fff", // dark → dark bg, light → white bg
          color: isDarkMode ? "#fff" : "#000",              // dark → white text, light → black text
          padding: "8px 12px",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.3)",
          border: isDarkMode ? "none" : "1px solid #ddd",   // light theme adds border
        }}
      >
        <p className="mb-1 fw-bold">{label}</p>
        <p className="mb-0">
          {payload[0].name}: {payload[0].value}
        </p>
      </div>
    );
  }
  return null;
};

// ✅ Reusable Stat Item Component
const StatItem = ({ icon, color, label, value, unit = "" }) => (
  <div className="stat-item d-flex align-items-center gap-2">
    <div className={`text-${color}`}>{icon}</div>
    <div>
      <p className="mb-0 fw-bold">{label}</p>
      <h6 className={`mb-0 text-${color}`}>
        {value}
        {unit}
      </h6>
    </div>
  </div>
);

const StudentDashboard = () => {
  const dispatch = useDispatch();
  const { user } = useSelector((state) => state.auth);
  const studentId = user?.id;

  const dashboard = useSelector((state) => state.dashboard) || {};

  const {
    studentName = "",
    learningStats = {
      total_learning_hours: 0,
      assignments_completed: 0,
      assignments_total: 0,
    },
    skills = [],
    weeklyLearningTrends = [],
    certificates = [],
    loading = false,
    error = null,
  } = dashboard;

  useEffect(() => {
    if (studentId) {
      dispatch(fetchDashboardData(studentId));
    }
  }, [dispatch, studentId]);

  if (error) return <p className="text-danger">Error: {error}</p>;

  return (
    <div className="dashboard-container p-4">
      {loading && (
        <div className="loading-overlay">
          <Spinner style={{ width: "3rem", height: "3rem" }} color="primary" />
        </div>
      )}

      {/* Welcome Section */}
      <div className="welcome-section mb-4">
        <h2 className="display-6 fw-bold mb-0">
          Welcome, {user?.username} 👋🏻
        </h2>
        <p className="text-muted">
          Keep up the great work on your learning journey!
        </p>
      </div>

      {/* Stats Row */}
      <div className="stats-grid d-flex flex-wrap gap-4 mb-4">
        <StatItem
          icon={<Clock size={22} />}
          color="primary"
          label="Total Learning Hours"
          value={learningStats.total_learning_hours}
          unit="h"
        />
        <StatItem
          icon={<BookOpen size={22} />}
          color="success"
          label="Total Assignments"
          value={learningStats.assignments_total}
        />
        <StatItem
          icon={<BookOpen size={22} />}
          color="success"
          label="Assignments Completed"
          value={learningStats.assignments_completed}
        />
      </div>

      {/* Charts Row */}
      <div className="charts-row d-flex gap-4 mb-4">
        {/* ✅ Skills Progress (Horizontal BarChart) */}
        <div className="skills-progress-card chart-card">
          <h5 className="fw-bold mb-3">Skills Progress</h5>
          {skills.length > 0 ? (
            <div className="chart-inner">
              <ResponsiveContainer width="100%" height={250}>
                <BarChart
                  data={skills}
                  layout="vertical"   // ✅ horizontal bars
                  margin={{ top: 0, right: 0, left: 0, bottom: 0 }}
                  barCategoryGap="20%"
                >
                  {/* X axis = progress values */}
                  <XAxis type="number" domain={[0, 100]} />

                  {/* Y axis = skill names */}
                  <YAxis dataKey="name" type="category" width={150} />

                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="progress" fill="#4f46e5" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-muted">No skills data available.</p>
          )}
        </div>

        {/* Weekly Learning Trends */}
        <div className="chart-card">
          <h5 className="fw-bold mb-3">Weekly Learning Trends</h5>
          {weeklyLearningTrends.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={weeklyLearningTrends}>
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip content={<CustomTooltip />} />
                <Line
                  type="monotone"
                  dataKey="hours"
                  stroke="#10b981"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted">No weekly trend data available.</p>
          )}
        </div>
      </div>

      {/* My Courses */}
      <div className="mb-4">
        <MyCourses />
      </div>

      {/* Certificates */}
      {/* {certificates?.length > 0 && (
        <div className="certificates">
          <h5 className="fw-bold mb-3">Certificates</h5>
          {certificates.map((cert, index) => (
            <div
              key={index}
              className="certificate-item d-flex align-items-center justify-content-between"
            >
              <div>
                <p className="mb-0 fw-bold">{cert.studentName}</p>
                <p className="mb-0 text-muted">{cert.courseName}</p>
              </div>
              <span className="text-warning d-flex align-items-center gap-1">
                <CheckCircle size={18} /> {cert.badge}
              </span>
            </div>
          ))}
        </div>
      )} */}
    </div>
  );
};

export default StudentDashboard;