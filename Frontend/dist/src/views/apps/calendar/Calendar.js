import { useEffect, useRef, memo } from 'react'
import '@fullcalendar/react/dist/vdom'
import FullCalendar from '@fullcalendar/react'
import listPlugin from '@fullcalendar/list'
import dayGridPlugin from '@fullcalendar/daygrid'
import timeGridPlugin from '@fullcalendar/timegrid'
import interactionPlugin from '@fullcalendar/interaction'
import { Menu } from 'react-feather'
import { Card, CardBody } from 'reactstrap'
import tippy from 'tippy.js'
import 'tippy.js/dist/tippy.css'
import { useNavigate } from "react-router-dom"
import '@styles/react/apps/app-calendar.scss'

const Calendar = props => {
  const calendarRef = useRef(null)
  const navigate = useNavigate()

  const {
    events,
    isRtl,
    calendarApi,
    setCalendarApi,
    toggleSidebar,
    sessions
  } = props

  // assign colors per course
  const courseColors = {}
  const colors = ['primary', 'success', 'danger', 'warning', 'info', 'secondary']
  sessions?.forEach((course, i) => {
    courseColors[course.course_name] = colors[i % colors.length]
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
      const courseName = event.extendedProps.courseName
      const colorName = courseColors[courseName] || 'primary'
      const isCompleted = event.extendedProps.completed
      return [
        `bg-light-${colorName}`,
        'fc-event-custom',
        isCompleted ? 'calendar-event-completed' : ''
      ]
    },

    eventClick({ event }) {
      const isCompleted = event.extendedProps.completed
      if (isCompleted) return
      const sessionId = event.extendedProps.sessionId
      const url = sessionId ? `/live-class/landing/${sessionId}` : `/live-class/landing`
      window.open(`${window.location.origin}${url}`, '_blank', 'noopener,noreferrer')
    },

    eventDidMount(info) {
      const isCompleted = info.event.extendedProps.completed
      tippy(info.el, {
        content: `${info.event.title}`,
        placement: 'top',
        arrow: true
      })

      if (isCompleted) {
        const completedDiv = document.createElement('div')
        completedDiv.innerHTML = `<span style="font-size:1.1em;">&#10003;</span> Completed`
        completedDiv.style.color = 'green'
        completedDiv.style.fontSize = '0.85em'
        completedDiv.style.marginTop = '2px'
        completedDiv.style.position = 'absolute'
        completedDiv.style.top = '100%'
        completedDiv.style.left = '0'
        completedDiv.style.background = '#fff'
        completedDiv.style.padding = '2px 8px'
        completedDiv.style.borderRadius = '4px'
        completedDiv.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)'
        completedDiv.style.zIndex = '10'
        completedDiv.style.display = 'none'

        info.el.style.position = 'relative'
        info.el.appendChild(completedDiv)

        info.el.addEventListener('mouseenter', () => {
          completedDiv.style.display = 'block'
        })
        info.el.addEventListener('mouseleave', () => {
          completedDiv.style.display = 'none'
        })
      }
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
