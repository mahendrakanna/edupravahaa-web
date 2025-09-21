import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiList from "../../api.json";
import api from "../utility/api";

const API_URL = import.meta.env.VITE_API_BASE_URL;

// Thunk to fetch teacher dashboard stats
export const fetchTeacherDashboard = createAsyncThunk(
  "teacherDashboard/fetchTeacherDashboard",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token || localStorage.getItem("access");
      console.log("token", token);

      const response = await api.get(`${API_URL}${apiList.dashboard.teacherStats}`, {
        headers: { Authorization: `Bearer ${token}` },
      });



      return response.data.data || {};
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message || "Something went wrong");
    }
  }
);

// Slice
const teacherDashboardSlice = createSlice({
  name: "teacherDashboard",
  initialState: {
    stats: null,
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchTeacherDashboard.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchTeacherDashboard.fulfilled, (state, action) => {
        state.loading = false;
        const payload = action.payload || {};
        state.stats = {
          totalTeachingHours: payload.stats?.totalTeachingHours || 0,
          activeStudents: payload.stats?.activeStudents || 0,
          upcomingClasses: payload.stats?.upcomingClasses || 0,
          nextClass: payload.stats?.nextClass || null,
          missingClasses: payload.stats?.missingClasses || 0,
          weeklyTrends: payload.weeklyTrends || [], // Chart data
        };
      })

      .addCase(fetchTeacherDashboard.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload || "Something went wrong!";
      });
},
});

export default teacherDashboardSlice.reducer;
