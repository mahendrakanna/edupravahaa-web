import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import { Col, Container, Row, Spinner, Alert } from "reactstrap"
import CourseCard from "./CourseCard"
import { fetchCourses } from "../../../redux/coursesSlice"

const Courses = () => {
  const dispatch = useDispatch()
  const { courses, loading, error } = useSelector((state) => state.courses)
  useEffect(() => {
    dispatch(fetchCourses())
  }, [dispatch])

  return (
<Container fluid className="my-courses-container py-2 rounded shadow-sm">
      <h2 className="mb-2 text-center">Our Courses</h2>

      {loading && (
      <div
        className="d-flex justify-content-center align-items-center"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          background: "transparent overlay", // transparent white overlay
          zIndex: 9999,
        }}
      >
        <Spinner style={{ width: "3rem", height: "3rem" }} color="primary" />
      </div>
    )}


      {error && <Alert color="danger">{error}</Alert>}

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
