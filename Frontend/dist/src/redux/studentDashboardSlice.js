// src/redux/dashboardSlice.js
import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";
import apiList from '../../api.json'
const API_URL = import.meta.env.VITE_API_BASE_URL;

// --- Thunk: Fetch Dashboard Data ---
export const fetchDashboardData = createAsyncThunk(
  "dashboard/fetchDashboardData",
  async (studentId, { rejectWithValue }) => {
    try {
      const response = await axios.get(API_URL+ apiList.student.student_dashboard+studentId);
      return response.data;
    } catch (error) {
      return rejectWithValue(error.response?.data || error.message);
    }
  }
);

const dashboardSlice = createSlice({
  name: "dashboard",
  initialState: {
    studentName: "",
    learningStats: { total_learning_hours: 0, assignments_completed: 0, assignments_total: 0 },
    skills: [],
    weeklyLearningTrends: [],
    certificates: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboardData.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDashboardData.fulfilled, (state, action) => {
        state.loading = false;
        state.studentName = action.payload.student_name;
        state.learningStats = action.payload.learning_stats;
        state.skills = action.payload.skills;
        state.weeklyLearningTrends = action.payload.weekly_learning_trends;
        state.certificates = action.payload.certificates;
      })
      .addCase(fetchDashboardData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export default dashboardSlice.reducer;
