// ** React Imports
import { lazy } from 'react'
import { Navigate } from 'react-router-dom'
import Courses from '../../views/apps/courses'
import MyCourses from '../../views/apps/mycourses'
import LiveClass from '../../views/apps/liveClass'


const Calendar = lazy(() => import('../../views/apps/calendar'))
// const DashboardAnalytics = lazy(() => import('../../views/dashboard/analytics'))
const DashboardEcommerce = lazy(() => import('../../views/dashboard/ecommerce'))


const AppRoutes = [
  {
    element: <Calendar />,
    path: '/calendar'
  },
  {
    element: <DashboardEcommerce />,
    path: '/dashboard'
  },

  {
    element: <Courses/>,
    path: '/courses'
  },
  {
    element: <MyCourses />,
    path: '/mycourses'
  },
  {
    element: <LiveClass />,
    path: '/live-class'
  }
]

export default AppRoutes
