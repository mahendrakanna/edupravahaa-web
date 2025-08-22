// ** Icons Import
import { Mail, MessageSquare, CheckSquare, Calendar, FileText, Circle, ShoppingCart, User, Shield } from 'react-feather'

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
    id: 'mycourses',
    title: 'My Courses',
    icon: <CheckSquare size={20} />,
    navLink: '/mycourses',
    
  },
   {
    id:'courses',
    title: 'Courses',
    icon: <FileText size={20} />,
    navLink: '/courses'
  },
  {
    id: 'calendar',
    title: 'Calendar',
    icon: <Calendar size={20} />,
    navLink: '/apps/calendar'
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
