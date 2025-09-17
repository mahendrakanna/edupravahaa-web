import { Fragment } from 'react'
import { Card, CardBody, Button, Input, Label } from 'reactstrap'
import illustration from '@src/assets/images/pages/calendar-illustration.png'

const SidebarLeft = ({ toggleSidebar, store, dispatch, updateFilter, updateAllFilters, sessions }) => {
  const courseNames = sessions?.map(c => c.course_name) || []

  const handleSelectAll = (checked) => {
    dispatch(updateAllFilters({ all: checked, sessions }))
  }

  return (
    <Fragment>
      <Card className='sidebar-wrapper shadow-none'>
        <CardBody className='card-body d-flex justify-content-center my-sm-0 mb-3'>
          <Button color='primary' block onClick={() => toggleSidebar(false)}>
            <span className='align-middle'>My Courses</span>
          </Button>
        </CardBody>

        <CardBody>
          <h5 className='section-label mb-1'>
            <span className='align-middle'>Filter Courses</span>
          </h5>

          {/* Select All */}
          <div className='form-check mb-1'>
            <Input
              id='view-all'
              type='checkbox'
              className='select-all'
              checked={store.selectedCalendars.length === courseNames.length}
              onChange={e => handleSelectAll(e.target.checked)}
            />
            <Label className='form-check-label' for='view-all'>View All</Label>
          </div>

          {/* Course checkboxes */}
          <div className='calendar-events-filter'>
            {sessions?.map((course, i) => (
              <div className='form-check' key={i}>
                <Input
                  type='checkbox'
                  id={`course-${i}`}
                  checked={store.selectedCalendars.includes(course.course_name)}
                  onChange={() => dispatch(updateFilter(course.course_name))}
                />
                <Label className='form-check-label' for={`course-${i}`}>
                  {course.course_name}
                </Label>
              </div>
            ))}
          </div>
        </CardBody>
      </Card>

      <div className='mt-auto'>
        <img className='img-fluid' src={illustration} alt='illustration' />
      </div>
    </Fragment>
  )
}

export default SidebarLeft
