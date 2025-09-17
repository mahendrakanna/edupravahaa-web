import { useState } from "react"
import {
  Card,
  CardBody,
  CardTitle,
  CardText,
  CardImg,
  CardFooter,
  Button,
  Modal,
  ModalHeader,
  ModalBody,
  ListGroup,
  ListGroupItem,
  Badge
} from "reactstrap"
import { FaCheckCircle, FaChartLine, FaClock } from "react-icons/fa"
import '@styles/react/pages/courses.scss'

const CourseCard = ({ course }) => {
  const [modal, setModal] = useState(false)
  const toggle = () => setModal(!modal)

  const courseData = course.course 

  // ✅ Fix property mismatch: use batchStartDate & batchEndDate
  const groupedSchedules = courseData.schedule?.reduce((acc, sched) => {
    if (!acc[sched.type]) {
      acc[sched.type] = { 
        ...sched, 
        sessions: sched.days.map((day) => ({
          day,
          time: sched.time,
          startDate: sched.batchStartDate,
          endDate: sched.batchEndDate
        }))
      }
    } else {
      sched.days.forEach((day) => {
        acc[sched.type].sessions.push({
          day,
          time: sched.time,
          startDate: sched.batchStartDate,
          endDate: sched.batchEndDate
        })
      })
    }
    return acc
  }, {})

  const batchList = groupedSchedules ? Object.values(groupedSchedules) : []

  return (
    <>
      <Card className="shadow-sm h-100 course-card">
        <CardImg
          top
          width="100%"
          height="200px"
          src={
            courseData.thumbnail ||
            "https://media.istockphoto.com/id/1353769234/photo/training-and-skill-development-concept-with-icons-of-online-course-conference-seminar-webinar.jpg?s=612x612&w=0&k=20&c=2YJG1My6Lu1T1FnzIPbimRNORcSbSuz6A8zb7HKNpx4="
          }
          alt={courseData.name}
        />
        <CardBody>
          <CardTitle tag="h5" className="fw-bold">
            {courseData.name}
          </CardTitle>
          <CardText className="text-muted">{courseData.description}</CardText>
        </CardBody>
        <CardFooter className="text-end">
          <Button color="primary" size="sm" onClick={toggle}>
            View Details →
          </Button>
        </CardFooter>
      </Card>

      {/* Modal */}
      <Modal isOpen={modal} toggle={toggle} size="lg" centered>
        <ModalHeader toggle={toggle} className="fw-bold modal-header-custom">
          {courseData.name}
        </ModalHeader>
        <ModalBody className="course-modal-body">
          <p className="lead">{courseData.description}</p>

          <h6 className="fw-bold mt-1">Key Advantages:</h6>
          <ListGroup flush>
            {courseData.advantages?.map((adv, idx) => (
              <ListGroupItem
                key={idx}
                className="d-flex align-items-center border-0 px-0"
              >
                <FaCheckCircle className="text-success me-2" /> {adv}
              </ListGroupItem>
            ))}
          </ListGroup>

          <h6 className="fw-bold mt-1">Your Batch:</h6>
          {batchList.map((batch, idx) => (
            <div key={idx} className="mb-1 p-1 border rounded shadow-sm">
              {batch.sessions.map((s, i) => (
                <p key={i} className="mb-1">
                  <FaClock className="me-2 text-secondary" />
                  {s.day}: {s.time}
                </p>
              ))}

              <Badge color="info" className="me-2">
                Starts from{" "}
                {new Date(batch.sessions[0].startDate).toLocaleDateString("en-US", {
                  day: "2-digit",
                  month: "long",
                  year: "numeric"
                })}
              </Badge>
              <Badge color="warning" className="me-2">
                Ends on{" "}
                {new Date(batch.sessions[0].endDate).toLocaleDateString("en-US", {
                  day: "2-digit",
                  month: "long",
                  year: "numeric"
                })}
              </Badge>
              <p className="mt-1">
                <strong>Type:</strong> {batch.type}
              </p>
            </div>
          ))}

          <div className="mt-1 d-flex justify-content-between">
            <span>
              <FaClock className="me-2 text-secondary" />
              Duration: {courseData.duration_hours} hrs
            </span>
            <span>
              <FaChartLine className="me-2 text-primary" />
              Price: ₹{courseData.base_price}
            </span>
          </div>

          {/* ✅ Purchased Info */}
          <div className="mt-1">
            <Badge color={course.payment_status ? "success" : "secondary"} className="p-1">
              Payment: {course.payment_status || "Not Paid"}
            </Badge>{" "}
            <Badge color="secondary" className="p-1">
              Purchased at:{" "}
              {course.purchased_at
                ? new Date(course.purchased_at).toLocaleString()
                : "N/A"}
            </Badge>
          </div>
        </ModalBody>
      </Modal>
    </>
  )
}

export default CourseCard
