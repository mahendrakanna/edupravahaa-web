import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../utility/api"; 
import apiList from "../../api.json";
import toast from 'react-hot-toast';

// ------------------ Thunks ------------------ //

export const fetchRecordedVideos = createAsyncThunk(
  "courses/fetchRecordedVideos",
  async (courseId, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      if (!apiList.classes.recordedVideos) {
        return rejectWithValue("RecordedVideos endpoint is undefined");
      }
      const url = courseId
        ? `${apiList.classes.recordedVideos}?course_id=${courseId}`
        : apiList.classes.recordedVideos;

      const response = await api.get(url, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      return response.data;
    } catch (err) {
      console.error("Error fetching recorded videos:", err.message, err.config?.url);
      const errorMessage =
        err.response?.data?.message || err.message || "Failed to fetch recorded videos";
      toast.error(errorMessage);
      return rejectWithValue(
        err.response?.data || err.message || "Failed to fetch recorded videos"
      );
    }
  }
);

export const uploadRecording = createAsyncThunk(
  "classes/uploadRecording",
  async ({ roomId, userId, blob }, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      if (!apiList.classes.uploadRecording) {
        return rejectWithValue("UploadRecording endpoint is undefined");
      }

      const formData = new FormData();
      formData.append("recording", blob, `class_${roomId}_${userId}.webm`);

      const response = await api.post(
        `${apiList.classes.uploadRecording.replace(":roomId", roomId)}`, 
        formData,
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "multipart/form-data",
          },
        }
      );

      return response.data;
    } catch (err) {
      console.error("Error uploading recording:", err.message, err.config?.url);
      const errorMessage =
        err.response?.data?.message || err.message || "Failed to upload recording";
      toast.error(errorMessage);
      return rejectWithValue(
        err.response?.data || err.message || "Failed to upload recording"
      );
    }
  }
);

// ------------------ Slice ------------------ //

const recordedVideosSlice = createSlice({
  name: "recordedVideos",
  initialState: {
    courses: [],          
    courseRecordings: [],
    loading: false,
    error: null,
    uploading: false,
    uploadError: null,
    uploadSuccess: false,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      // 🔹 fetchRecordedVideos
      .addCase(fetchRecordedVideos.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecordedVideos.fulfilled, (state, action) => {
          state.loading = false;
          if (action.meta.arg) {
            state.courseRecordings = action.payload.data || [];
          } else {
            // fetching all courses
            state.courses = action.payload.data || [];
          }
        })
      .addCase(fetchRecordedVideos.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      // 🔹 uploadRecording
      .addCase(uploadRecording.pending, (state) => {
        state.uploading = true;
        state.uploadError = null;
        state.uploadSuccess = false;
      })
      .addCase(uploadRecording.fulfilled, (state, action) => {
        state.uploading = false;
        state.uploadSuccess = true;
        toast.success("Recording uploaded successfully");
        // Optionally: push new recording into state
        // if (action.payload?.data) {
        //   state.recordedVideos.unshift(action.payload.data);
        // }
      })
      .addCase(uploadRecording.rejected, (state, action) => {
        state.uploading = false;
        state.uploadError = action.payload;
        state.uploadSuccess = false;
      });
  },
});

export default recordedVideosSlice.reducer;
