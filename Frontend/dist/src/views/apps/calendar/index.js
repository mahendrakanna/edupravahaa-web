// ** React Imports
import { Fragment, useState, useEffect } from 'react'
import classnames from 'classnames'
import { Row, Col } from 'reactstrap'
import Calendar from './Calendar'
import SidebarLeft from './SidebarLeft'
import { useSelector, useDispatch } from 'react-redux'
import { updateFilter, updateAllFilters } from './store'
import '@styles/react/apps/app-calendar.scss'
import { fetchMyCourses } from '../../../redux/coursesSlice'
import { useRTL } from '@hooks/useRTL'

const CalendarComponent = () => {
  const dispatch = useDispatch()
  const store = useSelector(state => state.calendar)
  const { mycourseslist } = useSelector((state) => state.courses)

  const [calendarApi, setCalendarApi] = useState(null)
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(false)
  const [isRtl] = useRTL()

  const toggleSidebar = val => setLeftSidebarOpen(val)

  const blankEvent = {
    title: '',
    start: '',
    end: '',
    allDay: false,
    url: '',
    extendedProps: { courseId: '', courseName: '' }
  }

  // fetch courses on mount
  useEffect(() => {
    dispatch(fetchMyCourses())
  }, [dispatch])

  // default select all when courses load
  useEffect(() => {
    if (mycourseslist?.length > 0) {
      dispatch(updateAllFilters({ all: true, mycourseslist }))
    }
  }, [mycourseslist, dispatch])

  // helper: build schedule dates
  function getScheduleDates(schedule) {
    const result = []
    schedule.forEach(sch => {
      const start = new Date(sch.startDate)
      const end = new Date(sch.endDate)
      let current = new Date(start)
      const daysOfWeek = sch.days.map(day => day.toLowerCase())
      while (current <= end) {
        const dayName = current.toLocaleString('en-US', { weekday: 'long' }).toLowerCase()
        if (daysOfWeek.includes(dayName)) {
          result.push({
            date: current.toISOString().split('T')[0],
            time: sch.time,
            type: sch.type
          })
        }
        current.setDate(current.getDate() + 1)
      }
    })
    return result
  }

  // helper: convert to 24h
  function convertTo24Hour(timeStr) {
    const [time, modifier] = timeStr.split(' ')
    let [hours, minutes] = time.split(':')
    hours = parseInt(hours, 10)
    if (modifier === 'PM' && hours < 12) hours += 12
    if (modifier === 'AM' && hours === 12) hours = 0
    return `${hours.toString().padStart(2, '0')}:${minutes}:00`
  }

  // build events from courses
  const courseEvents = mycourseslist?.flatMap(courseObj => {
    const course = courseObj.course
    const dates = getScheduleDates(course.schedule)

   return dates.map(d => {
    const [startTime, endTime] = d.time.split(' to ')
    const startDateTime = `${d.date}T${convertTo24Hour(startTime)}`
    const endDateTime = `${d.date}T${convertTo24Hour(endTime)}`
    const isCompleted = new Date(endDateTime) < new Date()
    return {
      title: `${course.name} – ${startTime}`,
      start: startDateTime,
      end: endDateTime,
      extendedProps: { 
        courseId: course.id,
        courseName: course.name,
        scheduleType: d.type,
        completed: isCompleted // <-- add this
      }
    }
    })
  }) || []

  // filter by selected courses
  const filteredEvents = courseEvents.filter(
    event => store.selectedCalendars.includes(event.extendedProps.courseId)
  )

  const eventsToShow = store.selectedCalendars.length > 0 ? filteredEvents : courseEvents

  return (
    <Fragment>
      <div className='app-calendar overflow-hidden border'>
        <Row className='g-0'>
          <Col
            id='app-calendar-sidebar'
            className={classnames('col app-calendar-sidebar flex-grow-0 overflow-hidden d-flex flex-column', {
              show: leftSidebarOpen
            })}
          >
            <SidebarLeft
              store={store}
              dispatch={dispatch}
              updateFilter={updateFilter}
              toggleSidebar={toggleSidebar}
              updateAllFilters={updateAllFilters}
              mycourseslist={mycourseslist}
            />
          </Col>
          <Col className='position-relative'>
            <Calendar
              isRtl={isRtl}
              store={store}
              events={eventsToShow}
              dispatch={dispatch}
              blankEvent={blankEvent}
              calendarApi={calendarApi}
              toggleSidebar={toggleSidebar}
              setCalendarApi={setCalendarApi}
              mycourseslist={mycourseslist}
            />
          </Col>
          <div
            className={classnames('body-content-overlay', { show: leftSidebarOpen === true })}
            onClick={() => toggleSidebar(false)}
          ></div>
        </Row>
      </div>
    </Fragment>
  )
}

export default CalendarComponent
