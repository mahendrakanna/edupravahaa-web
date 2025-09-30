import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import { Col, Container, Row } from "reactstrap"
import CourseCard from "./CourseCard"
import { fetchCourses } from "../../../redux/coursesSlice"
import ComponentSpinner from "../../../@core/components/spinner/Loading-spinner"

const Courses = () => {
  const dispatch = useDispatch()
  const { courses, loading, error } = useSelector((state) => state.courses)

  useEffect(() => {
    dispatch(fetchCourses())
  }, [dispatch])

  return (
    <Container fluid className="my-courses-container py-2 rounded shadow-sm">
      <h2 className="mb-2 text-center">Our Courses</h2>

      {loading && <ComponentSpinner />}

      {error && <p className="text-danger text-center">{error}</p>}

      {!loading && !error && courses.length === 0 && (
        <p className="text-center">No courses available.</p>
      )}

      <Row className="g-4">
        {!loading &&
          !error &&
          Array.isArray(courses) &&
          courses.map((course) => (
            <Col key={course.id} xs={12} sm={6} lg={4}>
              <CourseCard course={course} />
            </Col>
          ))}
      </Row>
    </Container>
  )
}

export default Courses
