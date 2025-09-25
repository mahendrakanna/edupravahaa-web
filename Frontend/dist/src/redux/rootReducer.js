// ** Reducers Imports
import navbar from './navbar'
import layout from './layout'
import auth from './authentication'

import calendar from '@src/views/apps/calendar/store'
import courses from './coursesSlice'
import meeting from './meetingSlice'
import recordedVideos from './recordedVideosSlice'

const rootReducer = {
  auth,
  navbar,
  layout,
  calendar,
  courses,
  meeting,
  recordedVideos

}

export default rootReducer
