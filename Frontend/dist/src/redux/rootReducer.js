// ** Reducers Imports
import navbar from './navbar'
import layout from './layout'
import auth from './authentication'

import calendar from '@src/views/apps/calendar/store'
import courses from './coursesSlice'

const rootReducer = {
  auth,
  navbar,
  layout,
  calendar,
  courses

}

export default rootReducer
