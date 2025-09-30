import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import api from "../utility/api"; 
import apiList from "../../api.json";
import toast from 'react-hot-toast';



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
      const errorMessage = err.response?.data?.message || err.message || "Failed to fetch courses";
      toast.error(errorMessage);
      return rejectWithValue(err.response?.data || err.message || "Failed to fetch courses");
    }
  }
);


export const enrollCourse = createAsyncThunk(
  "courses/enrollCourse",
  async ({ course, selectedSchedule, razorpay_key }, { rejectWithValue, getState, dispatch }) => {
    try {
      const { auth } = getState();
      const token = auth?.token;

      if (!token) {
        return rejectWithValue("No access token found");
      }

      if (!apiList.payments?.create_order) {
        return rejectWithValue("Create order endpoint is undefined");
      }

      // Build payload
      const payload = {
        course_id: course.id,
        batch: selectedSchedule.type,
        start_date: selectedSchedule.batchStartDate,
        end_date: selectedSchedule.batchEndDate,
      };

      if (selectedSchedule.type === "weekdays") {
        payload.time = selectedSchedule.time;
      } else if (selectedSchedule.type === "weekends") {
        payload.saturday_time = selectedSchedule.saturday_time;
        payload.sunday_time = selectedSchedule.sunday_time;
      }

      console.log("Enroll API Payload:", payload);

      // Call create_order
      const orderResponse = await api.post(
        apiList.payments.create_order,
        payload,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      const orderData = orderResponse.data.data;
      console.log("orderData", orderData);

      // Razorpay options
      const options = {
        key: razorpay_key,
        amount: orderData.amount,
        currency: orderData.currency,
        name: course.name,
        description: course.description,
        order_id: orderData.order_id,
        handler: async function (response) {
          console.log("Razorpay response:", response);
          try {
            const verifyRes = await api.post(
              apiList.payments.verify_payment,
              {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                subscription_id: orderData.subscription_id,
              },
              { headers: { Authorization: `Bearer ${token}` } }
            );

            toast.success("✅ Payment verified successfully!");
            dispatch(fetchCourses());
            dispatch(fetchMyCourses());
            // dispatch(getTrialPeriod()); // add if you have it in slice
          } catch (error) {
            console.error("Verification error:", error);
            toast.error("❌ Payment verification failed");
          }
        },
        prefill: {
          name: "John Doe",
          email: "john@example.com",
          contact: "9999999999",
        },
        theme: { color: "#3399cc" },
      };

      const rzp = new window.Razorpay(options);
      rzp.open();

      return orderResponse.data;
    } catch (err) {
      console.error("Enrollment error:", err.message, err.config?.url);
      const errorMessage =
        err.response?.data?.message || err.message || "Failed to enroll";
      toast.error(errorMessage);
      return rejectWithValue(err.response?.data || errorMessage);
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
      const errorMessage = err.response?.data?.message || err.message || "Failed to fetch my courses";
      toast.error(errorMessage);
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
      const errorMessage = err.response?.data?.message || err.message || "Failed to fetch sessions";
      toast.error(errorMessage);
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
        // Show success toast if there's a message
        if (action.payload.message) {
          toast.success(action.payload.message);
        }
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
        // Show success toast if there's a message
        if (action.payload.message) {
          toast.success(action.payload.message);
        }
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
        // Show success toast if there's a message
        if (action.payload.message) {
          toast.success(action.payload.message);
        }
      })
      .addCase(fetchSessions.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })

      .addCase(enrollCourse.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(enrollCourse.fulfilled, (state, action) => {
        state.loading = false;
        // success toast if API returned message
        if (action.payload?.message) {
          toast.success(action.payload.message);
        }
      })
      .addCase(enrollCourse.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

  },
});

export default coursesSlice.reducer;