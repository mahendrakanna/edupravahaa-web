// ** React Imports
import { lazy, useEffect } from 'react'
import { Navigate } from 'react-router-dom'
import Courses from '../../views/apps/courses'
import MyCourses from '../../views/apps/mycourses'
import Landing from '../../views/apps/liveClass'
import LiveClass from '../../views/apps/liveClass/liveClass'
import RecordedClasses from '../../views/apps/recordedvideos/recordedClasses'

// Open live class landing in a new tab/window, then navigate away
const LiveClassLauncher = () => {
  useEffect(() => {
    try {
      const url = `${window.location.origin}/live-class/landing`
      window.open(url, '_blank', 'noopener,noreferrer')
    } catch (e) {
      // ignore
    }
  }, [])
  return <Navigate to="/calendar" replace />
}


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
    element: <RecordedClasses />,
    path: '/recordedvideos',
    
  },
  {
    element: <LiveClassLauncher />,
    path: '/live-class',
    meta: { layout: 'blank', publicRoute: true }
  }
  ,
  { element: <Landing />, path: '/live-class/landing', meta: { layout: 'blank', publicRoute: true } },
  { element: <Landing />, path: '/live-class/landing/:roomId', meta: { layout: 'blank', publicRoute: true } },
  {
    element: <LiveClass />,
    path: '/live-class/session/:roomId',
    meta: { layout: 'blank', publicRoute: true }
  }
  ,
  {
    element: <LiveClass />,
    path: '/live-class/session',
    meta: { layout: 'blank', publicRoute: true }
  },
]

export default AppRoutes
