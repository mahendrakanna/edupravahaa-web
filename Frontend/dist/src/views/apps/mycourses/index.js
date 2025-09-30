import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import { fetchMyCourses } from "../../../redux/coursesSlice"
import { Col, Container, Row, Spinner, Alert } from "reactstrap"
import CourseCard from "./CourseCard"
import { useSkin } from '@hooks/useSkin'
import '@styles/react/pages/courses.scss'
import ComponentSpinner from "../../../@core/components/spinner/Loading-spinner"

const MyCourses = () => {
  const dispatch = useDispatch()
  const { mycourseslist, loading, error } = useSelector((state) => state.courses)
  const { skin } = useSkin()

  useEffect(() => {
    dispatch(fetchMyCourses())
  }, [dispatch])

  return (
    <Container fluid className="my-courses-container py-2 rounded shadow-sm">
      <h2 className="mb-2 text-center">My Courses</h2>

      {loading && <ComponentSpinner />}

      {error && <p className="text-danger text-center">{error}</p>}

      {!loading && !error && Array.isArray(mycourseslist) && mycourseslist.length === 0 && (
        <p className="text-center">No courses available.</p>
      )}

      <Row className="g-4">
        {!loading &&
          !error &&
          Array.isArray(mycourseslist) &&
          mycourseslist.map((course) => (
            <Col key={course.id} xs={12} sm={6} lg={4}>
              <CourseCard course={course} />
            </Col>
          ))}
      </Row>
    </Container>
  )
}

export default MyCourses
