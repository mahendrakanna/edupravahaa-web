import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../utility/api"; 
import apiList from "../../api.json";



export const fetchCourses = createAsyncThunk(
  "courses/fetchCourses",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      if (!apiList.course.courses) {
        return rejectWithValue("Courses endpoint is undefined");
      }

      const response = await api.get(apiList.course.courses, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      // console.log("Fetched courses:", response.data);
      return response.data;
    } catch (err) {
      console.error("Error fetching courses:", err.message, err.config?.url);
      return rejectWithValue(err.response?.data || err.message || "Failed to fetch courses");
    }
  }
);

export const fetchMyCourses = createAsyncThunk(
  "courses/fetchMyCourses",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      if (!apiList.course.mycourses) {
        return rejectWithValue("MyCourses endpoint is undefined");
      }

      const response = await api.get(apiList.course.mycourses, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (err) {
      console.error("Error fetching my courses:",err, err.message, err.config?.url); // Line ~46
      return rejectWithValue(err.response?.data || err.message || "Failed to fetch my courses");
    }
  }
);

export const fetchSessions = createAsyncThunk(
  "courses/fetchSessions",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      if (!apiList.classes.sessions) {
        return rejectWithValue("Sessions endpoint is undefined");
      }

      const response = await api.get(apiList.classes.sessions, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (err) {
      console.error("Error fetching sessions:", err.message, err.config?.url);
      return rejectWithValue(err.response?.data || err.message || "Failed to fetch sessions");
    }
  }
);

const coursesSlice = createSlice({
  name: "courses",
  initialState: {
    courses: [],
    mycourseslist: [],
    sessions: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCourses.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCourses.fulfilled, (state, action) => {
        state.loading = false;
        state.courses = action.payload.data || [];
      })
      .addCase(fetchCourses.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchMyCourses.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMyCourses.fulfilled, (state, action) => {
        state.loading = false;
        state.mycourseslist = action.payload.data || [];
      })
      .addCase(fetchMyCourses.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      
      .addCase(fetchSessions.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchSessions.fulfilled, (state, action) => {
        state.loading = false;
        state.sessions = action.payload.data || [];
      })
      .addCase(fetchSessions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

  },
});

export default coursesSlice.reducer;