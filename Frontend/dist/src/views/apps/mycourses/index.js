import { useEffect } from "react"
import { useDispatch, useSelector } from "react-redux"
import { fetchMyCourses } from "../../../redux/coursesSlice"
import { Col, Container, Row, Spinner, Alert } from "reactstrap"
import CourseCard from "./CourseCard"

const MyCourses = () => {

  const dispatch = useDispatch()
  const { mycourseslist, loading, error } = useSelector((state) => state.courses)
  useEffect(() => {
    dispatch(fetchMyCourses())
  }, [dispatch])
  console.log("My Courses:", mycourseslist)
  return (
    <Container fluid className="bg-white py-2 rounded shadow-sm">
      <h2 className="mb-2 text-center">My Courses </h2>

      {loading && (
        <div className="text-center my-4">
          <Spinner color="primary" />
        </div>
      )}

      {error && <Alert color="danger">{error}</Alert>}

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