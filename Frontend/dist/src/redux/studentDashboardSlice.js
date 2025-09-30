import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import apiList from "../../api.json";
import api from "../utility/api";

// --- Thunk: Fetch Dashboard Data ---
export const fetchDashboardData = createAsyncThunk(
  "dashboard/fetchDashboardData",
  async (studentId, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      console.log(`url: ${apiList.student.student_dashboard}${studentId}`);
      const response = await api.get(
        `${apiList.student.student_dashboard}${studentId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

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
    learningStats: {
      total_learning_hours: 0,
      assignments_completed: 0,
      assignments_total: 0,
    },
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
        const payload = action.payload?.data || action.payload;

        if (payload) {
          state.studentName = payload.student_name || "";
          state.learningStats = payload.learning_stats || {
            total_learning_hours: 0,
            assignments_completed: 0,
            assignments_total: 0,
          };
          state.skills = payload.skills || [];
          state.weeklyLearningTrends = payload.weekly_learning_trends || [];
          state.certificates = payload.certificates || [];
        }
      })
      .addCase(fetchDashboardData.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export default dashboardSlice.reducer;
