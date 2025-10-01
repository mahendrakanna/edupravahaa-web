import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { Clock, Users, Calendar, BookOpen, TrendingDown } from "react-feather";
import Avatar from "@components/avatar";
import { Spinner } from "reactstrap";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { fetchTeacherDashboard } from "../../../redux/teacherDashboardSlice";

import MyCourses from '../../apps/mycourses'
import SpinnerComponent from "../../../@core/components/spinner/Fallback-spinner";
import "@styles/react/pages/teacher-dashboard.scss"; 

// 🔹 Reusable Stat Item (inline style like DashboardStats)
const StatItem = ({ icon, color, label, value, unit = "" }) => (
  <div className="d-flex align-items-center gap-2">
    <Avatar color={`light-${color}`} icon={icon} />
    <div>
      <p className="mb-0 fw-bold">{label}</p>
      <h6 className={`mb-0 text-${color}`}>
        {value}
        {unit && <span className="ms-1">{unit}</span>}
      </h6>
    </div>
  </div>
);

const colors = {
  Sunday: "#f94144",
  Monday: "#f3722c",
  Tuesday: "#f8961e",
  Wednesday: "#f9c74f",
  Thursday: "#90be6d",
  Friday: "#43aa8b",
  Saturday: "#577590"
};

const TeacherDashboard = () => {
  const dispatch = useDispatch();
  const { stats, loading, error } = useSelector(
    (state) => state.teacherDashboard
  );

  const { user } = useSelector((state) => state.auth);

  useEffect(() => {
    dispatch(fetchTeacherDashboard());
  }, [dispatch]);

  if (loading)
    return (
      <SpinnerComponent />
    );

  if (error) {
    console.log("Dashboard Error:", error);
    return (
      <p className="text-danger">
        Error: {typeof error === "string" ? error : error.message}
      </p>
    );
  }

  if (!stats) return <p>No dashboard data available.</p>;


  return (
    <div className="dashboard-container p-1" style={{ fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif" }}>
      {/* 🔹 Welcome + Stats in one row */}
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-4">
        {/* Welcome Text */}
        <div className="flex-grow-1">
          <h2 className="fw-bold mb-1" style={{ fontSize: '1.5rem' }}> Welcome, {user?.first_name || user?.username || "Teacher"} 👋🏻</h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.95rem' }}>
            Keep up the great work on your teaching journey!
          </p>
        </div>

        {/* Stats Row */}
        <div className="d-flex flex-wrap align-items-center gap-3 mt-2">
          <StatItem
            icon={<Clock size={20} />}
            color="primary"
            label="Total Hours"
            value={stats?.totalTeachingHours || 0}
            unit="h"
          />
          <StatItem
            icon={<Users size={25} />}
            color="info"
            label="Active Students"
            value={stats?.activeStudents || 0}
          />
          <StatItem
            icon={<Calendar size={25} />}
            color="success"
            label="Upcoming Classes"
            value={stats?.upcomingClasses || 0}
          />
          <StatItem
            icon={<BookOpen size={25} />}
            color="warning"
            label="Next Class"
            value={
              stats?.nextClass
                ? `${stats.nextClass.course} – ${stats.nextClass.date}, ${stats.nextClass.time}`
                : "None"
            }
          />
          <StatItem
            icon={<TrendingDown size={25} />}
            color="danger"
            label="Missing Classes"
            value={stats?.missingClasses || 0}
          />
        </div>
      </div>

      {/* 🔹 Weekly Teaching Trends (Line Chart) */}
      <div className="row mt-2">
        <div className="col-12">
          <div className="card shadow-sm border-0 p-3">
            <h4 className="fw-bold mb-3">Weekly Teaching Trends</h4>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart
                data={stats?.weeklyTrends || []}
                margin={{ top: 20, right: 30, left: 0, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 14, fill: "#495057" }} />
                <YAxis tick={{ fontSize: 14, fill: "#495057" }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#f8f9fa",
                    borderRadius: "5px",
                    border: "1px solid #dee2e6",
                  }}
                  formatter={(value) => [`${value}h`, "Hours"]}
                />
                <Line
                  type="monotone"
                  dataKey="hours"
                  stroke="#7367f0"
                  strokeWidth={3}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      <div style={{ marginTop: '2rem' }}>
        <h3></h3>
        <MyCourses />
      </div>
    </div>
  );

};

export default TeacherDashboard;
