// ** Reducers Imports
import navbar from './navbar'
import layout from './layout'
import auth from './authentication'

import calendar from '@src/views/apps/calendar/store'
import courses from './coursesSlice'
// import meeting from './meetingSlice'
import meeting from './meetingSlice'
import dashboard from './studentDashboardSlice'


const rootReducer = {
  auth,
  navbar,
  layout,
  calendar,
  courses,
  // meeting

}

export default rootReducer
