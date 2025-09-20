  // ** Router imports
  import { lazy } from 'react'

  // ** Router imports
  import { useRoutes, Navigate } from 'react-router-dom'

  // ** Layouts
  import BlankLayout from '@layouts/BlankLayout'

  // ** Hooks Imports
  import { useLayout } from '@hooks/useLayout'

  // ** Utils
  import { getUserData, getHomeRouteForLoggedInUser } from '../utility/Utils'

  // ** GetRoutes
  import { getRoutes } from './routes'

  // ** Components
  const Error = lazy(() => import('../views/pages/misc/Error'))
  const Login = lazy(() => import('../views/pages/authentication/Login'))
  const NotAuthorized = lazy(() => import('../views/pages/misc/NotAuthorized'))
  const LiveClassLanding = lazy(() => import('../views/apps/liveClass'))

  const Router = () => {
    // ** Hooks
    const { layout } = useLayout()

    const allRoutes = getRoutes(layout)
    const getHomeRoute = () => {
      const user = getUserData()
      if (user) {
        // Prefer user_type (shape saved on login), fallback to role if present
        const roleOrType = user.user_type || user.role
        return getHomeRouteForLoggedInUser(roleOrType)
      } else {
        return '/login'
      }
    }

    const routes = useRoutes([
      {
        path: '/',
        index: true,
        element: <Navigate replace to={getHomeRoute()} />
      },
    {
      path: '/live-class/landing',
      element: <LiveClassLanding />
    },
    {
      path: '/live-class/landing/:roomId',
      element: <LiveClassLanding />
    },
    {
      path: '/live-class/landing',
      element: <BlankLayout />,
      children: [{ path: '/live-class/landing', element: <LiveClassLanding /> }]
    },
    {
      path: '/live-class/landing/:roomId',
      element: <BlankLayout />,
      children: [{ path: '/live-class/landing/:roomId', element: <LiveClassLanding /> }]
    },
      {
        path: '/login',
        element: <BlankLayout />,
        children: [{ path: '/login', element: <Login /> }]
      },
      {
        path: '/auth/not-auth',
        element: <BlankLayout />,
        children: [{ path: '/auth/not-auth', element: <NotAuthorized /> }]
      },
      {
        path: '*',
        element: <BlankLayout />,
        children: [{ path: '*', element: <Error /> }]
      },
      ...allRoutes
    ])

    return routes
  }

  export default Router
