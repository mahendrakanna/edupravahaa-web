import { useEffect, useRef, memo } from 'react'

// ** Full Calendar & it's Plugins
import '@fullcalendar/react/dist/vdom'
import FullCalendar from '@fullcalendar/react'
import listPlugin from '@fullcalendar/list'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'

// ** Third Party Components
import { Menu } from 'react-feather'
import { Card, CardBody } from 'reactstrap'
import tippy from 'tippy.js'
import 'tippy.js/dist/tippy.css'
import { useNavigate } from "react-router-dom";

const Calendar = props => {
  const calendarRef = useRef(null)
  const navigate = useNavigate();

  const {
    events,
    isRtl,
    calendarApi,
    setCalendarApi,
    toggleSidebar,
    mycourseslist
  } = props

  const courseColors = {}
  const colors = ['primary', 'success', 'danger', 'warning', 'info', 'secondary']
  mycourseslist?.forEach((courseObj, i) => {
    courseColors[courseObj.course.id] = colors[i % colors.length]
  })

  useEffect(() => {
    if (calendarApi === null) {
      setCalendarApi(calendarRef.current.getApi())
    }
  }, [calendarApi])

  const calendarOptions = {
    events: events || [],
    plugins: [interactionPlugin, dayGridPlugin, timeGridPlugin, listPlugin],
    initialView: 'dayGridMonth',
    headerToolbar: {
      start: 'sidebarToggle, prev,next, title',
      end: 'dayGridMonth,timeGridWeek,timeGridDay,listMonth'
    },
    editable: false,
    dayMaxEvents: 2,
    navLinks: true,

    eventClassNames({ event }) {
      const courseId = event.extendedProps.courseId
      const colorName = courseColors[courseId] || 'primary'
      return [`bg-light-${colorName}`, 'fc-event-custom']
    },

    eventClick({ event }) {
      const courseId = event.extendedProps.courseId
      console.log('Event clicked:', event)
      navigate(`/live-class/${courseId}`)
    },

    eventDidMount(info) {
      tippy(info.el, {
        content: info.event.title,
        placement: 'top',
        arrow: true
      })
    },

    customButtons: {
      sidebarToggle: {
        text: <Menu className='d-xl-none d-block' />,
        click() {
          toggleSidebar(true)
        }
      }
    },

    ref: calendarRef,
    direction: isRtl ? 'rtl' : 'ltr'
  }

  return (
    <Card className='shadow-none border-0 mb-0 rounded-0'>
      <CardBody className='pb-0'>
        <FullCalendar {...calendarOptions} />
      </CardBody>
    </Card>
  )
}

export default memo(Calendar)
