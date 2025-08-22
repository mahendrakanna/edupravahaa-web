import { createSlice, createAsyncThunk } from "@reduxjs/toolkit"
import axios from "axios"
import apiList from "../../api.json"

const BASE_URL = import.meta.env.VITE_API_BASE_URL

// get all courses
export const fetchCourses = createAsyncThunk(
  "courses/fetchCourses",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState()
      const token = auth?.token

      const response = await axios.get(BASE_URL + apiList.course.courses, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`
        }
      })
      console.log("Fetched courses:", response.data)
      return response.data
    } catch (err) {
      console.error("Error fetching courses:", err)
      return rejectWithValue(err.response?.data || "Failed to fetch courses")
    }
  }
)

// get my enrolled courses
export const fetchMyCourses = createAsyncThunk(
  "courses/fetchMyCourses",
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState()
      const token = auth?.token
      const response = await axios.get(BASE_URL + apiList.course.mycourses, {
        headers: {
          accept: "application/json",
          Authorization: `Bearer ${token}`
        }
      })
      console.log("Fetched my courses:", response.data)
      return response.data
    } catch (err) {
      console.error("Error fetching my courses:", err)
      return rejectWithValue(err.response?.data || "Failed to fetch my courses")
    }
  }
)

const coursesSlice = createSlice({
  name: "courses",
  initialState: {
    courses: [],
    mycourseslist: [],
    loading: false,
    error: null
  },
  reducers: {},
  extraReducers: (builder) => {
    builder
      // ---------------- All Courses ----------------
      .addCase(fetchCourses.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchCourses.fulfilled, (state, action) => {
        state.loading = false
        state.courses = action.payload.results || []
      })
      .addCase(fetchCourses.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })

      // ---------------- My Courses ----------------
      .addCase(fetchMyCourses.pending, (state) => {
        state.loading = true
        state.error = null
      })
      .addCase(fetchMyCourses.fulfilled, (state, action) => {
        state.loading = false
        state.mycourseslist = action.payload.results || []
      })
      .addCase(fetchMyCourses.rejected, (state, action) => {
        state.loading = false
        state.error = action.payload
      })
  }
})

export default coursesSlice.reducer
