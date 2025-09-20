// ** Icons Import
import { Mail, MessageSquare, CheckSquare, Calendar, FileText, Circle, ShoppingCart, User, Shield, Home } from 'react-feather'

export default [
  // {
  //   header: 'Apps & Pages'
  // },
  // {
  //   id: 'chat',
  //   title: 'Chat',
  //   icon: <MessageSquare size={20} />,
  //   navLink: '/apps/chat'
  // },
  {
    id:'dashboard',
    title: 'Dashboard',
    icon: <Home size={20} />,
    navLink: '/dashboard',
    roles:['teacher']
  },
  {
    id:'studnet',
    title: 'student dashboard',
    icon: <FileText size={20} />,
    navLink: '/student-dashboard',
    roles: ['student']
  },
  {
    id: 'mycourses',
    title: 'My Courses',
    icon: <CheckSquare size={20} />,
    navLink: '/mycourses',
    roles: ['student','teacher']
    
  },
   {
    id:'courses',
    title: 'Courses',
    icon: <FileText size={20} />,
    navLink: '/courses',
    roles: ['student', 'admin']
  },
  {
    id: 'calendar',
    title: 'Calendar',
    icon: <Calendar size={20} />,
    navLink: '/calendar',
    roles: ['student', 'teacher']
  },

  //   {
  //   id: 'courses',
  //   title: 'courses',
  //   icon: <FileText size={20} />,
  //   children: [
  //     {
  //       id: 'mycourses',
  //       title: 'My Courses',
  //       icon: <Circle size={12} />,
  //       navLink: '/mycourses'
  //     },
  //     {
  //       id: 'courses',
  //       title: 'Courses',
  //       icon: <Circle size={12} />,
  //       navLink: '/courses'
  //     },
  //     {
  //       id: 'calendar',
  //       title: 'Calendar',
  //       icon: <Circle size={12} />,
  //       navLink: '/apps/calendar'
  //     },
  //     {
  //       id: 'invoiceAdd',
  //       title: 'Add',
  //       icon: <Circle size={12} />,
  //       navLink: '/apps/invoice/add'
  //     }
  //   ]
  // },
]
