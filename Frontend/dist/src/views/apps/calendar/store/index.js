// ** Redux Imports
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'

// ** Axios Imports
import axios from 'axios'

export const fetchEvents = createAsyncThunk('appCalendar/fetchEvents', async calendars => {
  const response = await axios.get('/apps/calendar/events', { calendars })
  return response.data
})

export const addEvent = createAsyncThunk('appCalendar/addEvent', async (event, { dispatch, getState }) => {
  await axios.post('/apps/calendar/add-event', { event })
  await dispatch(fetchEvents(getState().calendar.selectedCalendars))
  return event
})

export const updateEvent = createAsyncThunk('appCalendar/updateEvent', async (event, { dispatch, getState }) => {
  await axios.post('/apps/calendar/update-event', { event })
  await dispatch(fetchEvents(getState().calendar.selectedCalendars))
  return event
})

export const updateFilter = createAsyncThunk(
  'appCalendar/updateFilter',
  async (filter, { dispatch, getState }) => {
    const { selectedCalendars } = getState().calendar
    let updatedFilters = []

    if (selectedCalendars.includes(filter)) {
      updatedFilters = selectedCalendars.filter(i => i !== filter)
    } else {
      updatedFilters = [...selectedCalendars, filter]
    }

    // await dispatch(fetchEvents(updatedFilters))
    return filter
  }
)


export const updateAllFilters = createAsyncThunk(
  'appCalendar/updateAllFilters',
  async ({ all, sessions }, { dispatch }) => {
    const courseNames = sessions?.map(c => c.course_name) || []
    if (all) {
      // await dispatch(fetchEvents(courseNames))
      return courseNames
    } else {
      // await dispatch(fetchEvents([]))
      return []
    }
  }
)


export const removeEvent = createAsyncThunk('appCalendar/removeEvent', async id => {
  await axios.delete('/apps/calendar/remove-event', { id })
  return id
})

export const appCalendarSlice = createSlice({
  name: 'appCalendar',
  initialState: {
    events: [],
    selectedEvent: {},
    selectedCalendars: ['Personal', 'Business', 'Family', 'Holiday', 'ETC']
  },
  reducers: {
    selectEvent: (state, action) => {
      state.selectedEvent = action.payload
    }
  },
  extraReducers: builder => {
    builder
      .addCase(fetchEvents.fulfilled, (state, action) => {
        state.events = action.payload
      })
      .addCase(updateFilter.fulfilled, (state, action) => {
        if (state.selectedCalendars.includes(action.payload)) {
          state.selectedCalendars.splice(state.selectedCalendars.indexOf(action.payload), 1)
        } else {
          state.selectedCalendars.push(action.payload)
        }
      })
      .addCase(updateAllFilters.fulfilled, (state, action) => {
  state.selectedCalendars = action.payload
})
  }
})

export const { selectEvent } = appCalendarSlice.actions

export default appCalendarSlice.reducer
