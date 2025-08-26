// ** React Imports
import { lazy } from 'react'
import { Navigate } from 'react-router-dom'
import Courses from '../../views/apps/courses'
import MyCourses from '../../views/apps/mycourses'


const Calendar = lazy(() => import('../../views/apps/calendar'))


const AppRoutes = [
  {
    element: <Calendar />,
    path: '/apps/calendar'
  },

  {
    element: <Courses/>,
    path: '/courses'
  },
  {
    element: <MyCourses />,
    path: '/mycourses'
  },
]

export default AppRoutes
