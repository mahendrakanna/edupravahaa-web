import { lazy } from 'react'
const Profile = lazy(() => import('../../views/pages/profile'))

const AccountSettings = lazy(() => import('../../views/pages/account-settings'))


const PagesRoutes = [
  {
    path: '/pages/profile',
    element: <Profile />
  },
  {
    path: '/pages/account-settings',
    element: <AccountSettings />
  },

  
 
 

 
]

export default PagesRoutes
