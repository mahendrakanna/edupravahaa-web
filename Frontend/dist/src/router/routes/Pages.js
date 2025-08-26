import { lazy } from 'react'
const Profile = lazy(() => import('../../views/pages/profile'))




const PagesRoutes = [
  {
    path: '/pages/profile',
    element: <Profile />
  },


  
 
 

 
]

export default PagesRoutes
