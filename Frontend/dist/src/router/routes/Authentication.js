// ** React Imports
import { lazy } from 'react'

const Login = lazy(() => import('../../views/pages/authentication/Login'))
const LoginCover = lazy(() => import('../../views/pages/authentication/LoginCover'))
const ForgotPassword = lazy(() => import('../../views/pages/authentication/ForgotPassword'))

const Register = lazy(() => import('../../views/pages/authentication/Register'))

const AuthenticationRoutes = [
  {
    path: '/login',
    element: <Login />,
    meta: {
      layout: 'blank',
      publicRoute: true,
      restricted: true
    }
  },

  {
    path: '/pages/login-cover',
    element: <LoginCover />,
    meta: {
      layout: 'blank'
    }
  },
  {
    path: '/forgot-password',
    element: <ForgotPassword />,
    layout: 'BlankLayout',
    meta: {
      layout: 'blank',
      publicRoute: true,
      restricted: true
    }
  },
    {
    path: '/register',
    element: <Register />,
    meta: {
      layout: 'blank',
      publicRoute: true,
      restricted: true
    }
  },

]

export default AuthenticationRoutes
