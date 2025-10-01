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
import { useSelector } from "react-redux"

const CourseCard = ({ course }) => {
  const [modal, setModal] = useState(false)
  const {user} = useSelector(state => state.auth)
  const toggle = () => setModal(!modal)

  const courseData = course.course || {}
 
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
          {courseData?.name}
        </ModalHeader>
        <ModalBody className="course-modal-body">
          <p className="lead">{courseData.description}</p>

          <h6 className="fw-bold mt-1">Key Advantages:</h6>
          <ListGroup flush>
            {courseData?.advantages?.map((adv, idx) => (
              <ListGroupItem
                key={idx}
                className="d-flex align-items-center border-0 px-0"
              >
                <FaCheckCircle className="text-success me-2" /> {adv}
              </ListGroupItem>
            ))}
          </ListGroup>

          <h6 className="fw-bold mt-1">Your Batch:</h6>
            {courseData.schedule && courseData.schedule.length > 0 ? (
              courseData.schedule.map((sched, idx) => (
                <div key={idx} className="mb-2 p-2 border rounded shadow-sm">
                  <h6 className="fw-bold">Batch {idx + 1} ({sched.type})</h6>

                  {sched.type === "weekdays" ? (
                    <p className="mb-1">
                      <FaClock className="me-2 text-secondary" />
                      {sched.days?.join(", ")} → {sched.time}
                    </p>
                  ) : (
                    <>
                      <p className="mb-1">
                        <FaClock className="me-2 text-secondary" />
                        Saturday → {sched.saturday_time}
                      </p>
                      <p className="mb-1">
                        <FaClock className="me-2 text-secondary" />
                        Sunday → {sched.sunday_time}
                      </p>
                    </>
                  )}

                  <div className="d-flex justify-content-between mt-1">
                    <Badge color="info">
                      📅 Starts:{" "}
                      {new Date(sched.batchStartDate).toLocaleDateString("en-US", {
                        day: "2-digit",
                        month: "long",
                        year: "numeric"
                      })}
                    </Badge>
                    <Badge color="warning">
                      🏁 Ends:{" "}
                      {new Date(sched.batchEndDate).toLocaleDateString("en-US", {
                        day: "2-digit",
                        month: "long",
                        year: "numeric"
                      })}
                    </Badge>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-muted fw-bold">Coming Soon</p>
            )}


          <div className="mt-1 d-flex justify-content-between">
            {/* <span>
              <FaClock className="me-2 text-secondary" />
              Duration: {courseData.duration_hours} hrs
            </span> */}
             {user && user.role === "student" && (
            <span>
              <FaChartLine className="me-2 text-primary" />
              Price: ₹{courseData?.price}
            </span>
          )}
          </div>

          {/* ✅ Purchased Info */}
          {user && user.role === "student" && (
            <div className="mt-1">
            <Badge color={course?.payment_status ? "success" : "secondary"} className="p-1">
              Payment: {course?.payment_status || "Not Paid"}
            </Badge>{" "}
            <Badge color="secondary" className="p-1">
              Purchased at:{" "}
              {course?.purchased_at
                ? new Date(course?.purchased_at).toLocaleString()
                : "N/A"}
            </Badge>
          </div>
          )
            }
          
        </ModalBody>
      </Modal>
    </>
  )
}

export default CourseCard
