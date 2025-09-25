import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../utility/api"; 
import apiList from "../../api.json";
import toast from 'react-hot-toast';



export const fetchRecordedVideos = createAsyncThunk(
  "courses/fetchRecordedVideos",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }
      if (!apiList.classes.recordedVideos) {
        return rejectWithValue("RecordedVideos endpoint is undefined");
      }

      const response = await api.get(apiList.classes.recordedVideos, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`,
        },
      });
      return response.data;
    } catch (err) {
      console.error("Error fetching recorded videos:", err.message, err.config?.url);
      const errorMessage = err.response?.data?.message || err.message || "Failed to fetch recorded videos";
      toast.error(errorMessage);
      return rejectWithValue(err.response?.data || err.message || "Failed to fetch recorded videos");
    }
  }
);


const recordedVideosSlice = createSlice({
  name: "recordedVideos",
  initialState: {
    recordedVideos: [],
    loading: false,
    error: null,
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchRecordedVideos.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecordedVideos.fulfilled, (state, action) => {
        state.loading = false;
        state.recordedVideos = action.payload.data || [];
        // Show success toast if there's a message
        if (action.payload.message) {
          toast.success(action.payload.message);
        }
      })
      .addCase(fetchRecordedVideos.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      }) 

  },
});
    
export default recordedVideosSlice.reducer;