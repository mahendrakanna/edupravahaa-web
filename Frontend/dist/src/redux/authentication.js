import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import axios from 'axios';
import apiList from '../../api.json'
import api from "../utility/api"

const API_URL = import.meta.env.VITE_API_BASE_URL;

// Thunks
export const signupUser = createAsyncThunk(
  'auth/signupUser',
  async (userData, { rejectWithValue }) => {
    try {
      const response = await axios.post(API_URL + apiList.auth.signup, userData);
      // console.log("Response Data:", response.data);

      return response.data;
    } catch (err) {
        // console.error("Error during signup:", err);
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const sendOtp = createAsyncThunk(
  'auth/sendOtp',
  async ( userData, { rejectWithValue }) => {
    try {
      const response = await axios.post(API_URL + apiList.auth.sendOtp, userData);
      return response.data;

    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const verifyOtp = createAsyncThunk(
  'auth/verifyOtp',
  async (otpverifydata, { rejectWithValue }) => {
    try {
      const response = await axios.post(API_URL + apiList.auth.verifyOtp, otpverifydata);
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const loginUser = createAsyncThunk(
  'auth/loginUser',
  async (credentials, { rejectWithValue }) => {
    try {
      const response = await axios.post(API_URL + apiList.auth.login, credentials);
      return response.data;

    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const getProfile = createAsyncThunk(
  'auth/getProfile',
  async (_, { rejectWithValue, getState }) => {
    try {
      const token = getState().auth.token;
      const response = await axios.get(API_URL + apiList.auth.getProfile, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const forgotPassword = createAsyncThunk(
  'auth/forgotPassword',
  async (payload, { rejectWithValue }) => {
    try {
      const response = await axios.post(
        API_URL + apiList.auth.forgotPassword,
        payload
      );
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

export const getTrialPeriod = createAsyncThunk(
  'auth/getTrialPeriod',
  async (_, { rejectWithValue, getState }) => {
    try {
      const token = getState().auth.token;
      const response = await axios.get(API_URL + apiList.student.trialStatus, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

// logout API 
export const logoutUser = createAsyncThunk(
  'auth/logoutUser',
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const refreshToken = auth.refreshToken;
      const accessToken = auth.token;
      // console.log("acc",accessToken)

      const response = await axios.post(
        API_URL + apiList.auth.logout,
        { refresh: refreshToken },
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${accessToken}`,
          },
        }
      );

      return response.data;
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

// refresh token api
export const refreshTokenThunk = createAsyncThunk(
  'auth/refreshToken',
  async (_, { rejectWithValue, getState }) => {
    try {
      const { auth } = getState();
      const refreshToken = auth.refreshToken;

      if (!refreshToken) {
        return rejectWithValue('No refresh token found');
      }

      // ⚡ use plain axios, not `api`
      const response = await axios.post(
        API_URL + apiList.auth.refresh,
        { refresh: refreshToken },
        { headers: { 'Content-Type': 'application/json' } }
      );

      return response.data; // { access: "...", refresh?: "..." }
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message);
    }
  }
);

// update password api
export const updatePassword = createAsyncThunk(
  'auth/updatePassword',
  async (payload, { rejectWithValue, getState }) => {
    try {
      const token = getState().auth.token
      const response = await axios.put(
        API_URL + apiList.auth.updatePassword,
        payload,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      )
      return response.data
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message)
    }
  }
)



// ** Update Profile
export const updateProfile = createAsyncThunk(
  'auth/updateProfile',
  async (payload, { rejectWithValue, getState }) => {
    try {
      const token = getState().auth.token
      const response = await axios.put(
        API_URL + apiList.auth.getProfile, 
        payload,
        {
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
        }
      )
      return response.data
    } catch (err) {
      return rejectWithValue(err.response?.data || err.message)
    }
  }
)



const authSlice = createSlice({
  name: 'auth',
  initialState: {
  user: JSON.parse(localStorage.getItem('userData')) || null,
  token: localStorage.getItem('access') || null,
  refreshToken: localStorage.getItem('refresh') || null,
  trialPeriodData: null,
  loading: false,
  error: null,
  success: false,
},
  reducers: {
    logout: (state) => {
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      localStorage.removeItem('userData');
    },
  },
  extraReducers: (builder) => {
    // Signup
    builder.addCase(signupUser.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(signupUser.fulfilled, (state, action) => {
      state.loading = false;
      state.success = true;
    });
    builder.addCase(signupUser.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
    });

    // OTP Verification
    builder.addCase(verifyOtp.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(verifyOtp.fulfilled, (state) => {
      state.loading = false;
      state.success = true;
    });
    builder.addCase(verifyOtp.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
    });

      // --- Send OTP
      builder.addCase(sendOtp.pending, (state) => {
        state.loading = true;
        state.error = null;
      });
      builder.addCase(sendOtp.fulfilled, (state, action) => {
        state.loading = false;
        state.success = true;       // ✅ request succeeded
      });
      builder.addCase(sendOtp.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });

    // Login
    builder.addCase(loginUser.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(loginUser.fulfilled, (state, action) => {
      // console.log("Login successful:", action.payload);

      state.loading = false;

      // ✅ Save tokens properly
      state.token = action.payload.access;
      state.refreshToken = action.payload.refresh;

      state.user = {
        user_type: action.payload.user_type,
        is_trial: action.payload.is_trial,
        has_purchased: action.payload.has_purchased,
        trial_ends_at: action.payload.trial_ends_at,
        trial_remaining_seconds: action.payload.trial_remaining_seconds,
      };

      // ✅ Store in localStorage
      localStorage.setItem('access', action.payload.access);
      localStorage.setItem('refresh', action.payload.refresh);
      localStorage.setItem('userData', JSON.stringify(state.user));
    });

    builder.addCase(loginUser.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
    });

    // Profile
    builder.addCase(getProfile.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(getProfile.fulfilled, (state, action) => {
      state.loading = false;
      state.user = action.payload.data;
      localStorage.setItem("userData", JSON.stringify(action.payload.data));
    });
    builder.addCase(getProfile.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
    });
      // Forgot Password
    builder.addCase(forgotPassword.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(forgotPassword.fulfilled, (state) => {
      state.loading = false;
      state.success = true;
    });
    builder.addCase(forgotPassword.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
    });

    // trail period
    builder.addCase(getTrialPeriod.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(getTrialPeriod.fulfilled, (state, action) => {
      state.loading = false;
      state.trialPeriodData = action.payload;
    });
    builder.addCase(getTrialPeriod.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
    });
    // log out 
     builder.addCase(logoutUser.pending, (state) => {
      state.loading = true;
      state.error = null;
    });
    builder.addCase(logoutUser.fulfilled, (state) => {
      state.loading = false;
      state.user = null;
      state.token = null;
      state.refreshToken = null;

      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      localStorage.removeItem('userData');
    });
    builder.addCase(logoutUser.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      localStorage.removeItem('userData');
    });

    // refresh token api 
    builder.addCase(refreshTokenThunk.pending, (state) => {
    state.loading = true;
    state.error = null;
    });
    builder.addCase(refreshTokenThunk.fulfilled, (state, action) => {
      state.loading = false;
      state.token = action.payload.access;

      localStorage.setItem('access', action.payload.access);

      if (action.payload.refresh) {
        state.refreshToken = action.payload.refresh; 
        localStorage.setItem('refresh', action.payload.refresh);
      }
    });
    builder.addCase(refreshTokenThunk.rejected, (state, action) => {
      state.loading = false;
      state.error = action.payload;
      state.user = null;
      state.token = null;
      state.refreshToken = null;
      localStorage.removeItem('access');
      localStorage.removeItem('refresh');
      localStorage.removeItem('userData');
    });

    // Update Password
  builder.addCase(updatePassword.pending, (state) => {
    state.loading = true
    state.error = null
  })
  builder.addCase(updatePassword.fulfilled, (state, action) => {
    state.loading = false
    state.success = true
  })
  builder.addCase(updatePassword.rejected, (state, action) => {
    state.loading = false
    state.error = action.payload
  })

  // Update Profile
  builder.addCase(updateProfile.pending, (state) => {
    state.loading = true
    state.error = null
  })
  builder.addCase(updateProfile.fulfilled, (state, action) => {
    state.loading = false
    state.user = action.payload.data 
    localStorage.setItem('userData', JSON.stringify(action.payload.data))
  })
  builder.addCase(updateProfile.rejected, (state, action) => {
    state.loading = false
    state.error = action.payload
  })

  
  },
  
});

export const { logout } = authSlice.actions;
export default authSlice.reducer;
