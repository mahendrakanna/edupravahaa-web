import React, { useEffect } from "react";
import { Clock, BookOpen, CheckCircle } from "react-feather";
import { useDispatch, useSelector } from "react-redux";
import { fetchDashboardData } from "../../../redux/studentDashboardSlice";
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

// Reusable Stat Item
const StatItem = ({ icon, color, label, value, unit = "" }) => (
  <div className="d-flex align-items-center gap-2 bg-white rounded-2xl shadow-md p-3">
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
    const {user} = useSelector((state) => state.auth);
    const studentId = user?.id; 
  const dispatch = useDispatch();
  const {
    studentName,
    learningStats,
    skills,
    weeklyLearningTrends,
    certificates,
    loading,
    error,
  } = useSelector((state) => state.dashboard);

  useEffect(() => {
    dispatch(fetchDashboardData(studentId));
  }, [dispatch, studentId]);

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="text-danger">Error: {error}</p>;

  return (
    <div className="p-4 dashboard-container">
      {/* Welcome */}
      <div className="welcome-section mb-4">
        <h2 className="display-6 fw-bold mb-0">Welcome, student 👋🏻</h2>
        <p className="text-muted">Keep up the great work on your learning journey!</p>
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
          label="Assignments Completed"
          value={learningStats.assignments_completed}
          unit={` / ${learningStats.assignments_total}`}
        />
      </div>

      {/* Skills Progress */}
      <div className="rounded-2xl shadow-md bg-white p-4 mb-4">
        <h5 className="fw-bold mb-3">Skills Progress</h5>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={skills}>
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="progress" fill="#4f46e5" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Weekly Trends */}
      <div className="rounded-2xl shadow-md bg-white p-4 mb-4">
        <h5 className="fw-bold mb-3">Weekly Learning Trends</h5>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={weeklyLearningTrends}>
            <XAxis dataKey="day" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="hours" stroke="#10b981" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Certificates */}
      {certificates?.length > 0 && (
        <div className="rounded-2xl shadow-md bg-white p-4">
          <h5 className="fw-bold mb-3">Certificates</h5>
          {certificates.map((cert, index) => (
            <div
              key={index}
              className="d-flex align-items-center justify-content-between border-bottom py-2"
            >
              <div>
                <p className="mb-0 fw-bold">{cert.studentName}</p>
                <p className="mb-0 text-muted">{cert.courseName}</p>
              </div>
              <span className="text-warning">
                <CheckCircle /> {cert.badge}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentDashboard;
