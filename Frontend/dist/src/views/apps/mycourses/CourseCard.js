import { useState } from "react"
import {
  Card,
  CardBody,
  CardTitle,
  CardText,
  CardImg,
  CardFooter,
  Button,
} from "reactstrap"
import {  FaChartLine, FaClock } from "react-icons/fa"


const CourseCard = ({ course }) => {
  const [modal, setModal] = useState(false)
  const toggle = () => setModal(!modal)
console.log("kav",course)
  return (
    <>
      <Card className="shadow-sm h-100 course-card">
        <CardImg
          top
          width="100%"
          height="200px"
          src={
            course.course.thumbnail ||
            "https://media.istockphoto.com/id/1353769234/photo/training-and-skill-development-concept-with-icons-of-online-course-conference-seminar-webinar.jpg?s=612x612&w=0&k=20&c=2YJG1My6Lu1T1FnzIPbimRNORcSbSuz6A8zb7HKNpx4="
          }
          alt={course.course.name}
        />
        <CardBody>
          <CardTitle tag="h5" className="fw-bold">
            {course?.course?.name}
          </CardTitle>
          <CardText className="text-muted">{course.course.description}</CardText>
          <div className="d-flex justify-content-between mt-2">
            <span>
              <FaClock className="me-1 text-secondary" />
              {course.course.duration_hours} hrs
            </span>
            <span> 
              <FaChartLine className="text-primary me-1" />
              ₹{course.course.base_price}
            </span>
          </div>
        </CardBody>
        {/* <CardFooter className="text-end">
          <Button color="primary" size="sm" onClick={toggle}>
            View Details →
          </Button>
        </CardFooter> */}
      </Card>

 
    </>
  )
}

export default CourseCard
