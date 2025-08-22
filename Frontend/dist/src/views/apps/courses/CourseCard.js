import { useState } from "react"
import { useDispatch, useSelector } from "react-redux"
import { useNavigate } from "react-router-dom"
import axios from "axios"
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
  ModalFooter,
  ListGroup,
  ListGroupItem
} from "reactstrap"
import { FaCheckCircle, FaChartLine, FaClock } from "react-icons/fa"
import toast from "react-hot-toast"
import "./CourseCard.css"
import { fetchCourses } from "../../../redux/coursesSlice"

const CourseCard = ({ course }) => {
  const [modal, setModal] = useState(false)
  const toggle = () => setModal(!modal)

  const token = useSelector((state) => state.auth.token)
  const razorpay_key = import.meta.env.VITE_RAZORPAY_KEY
  const BaseUrl = import.meta.env.VITE_API_BASE_URL
  const navigate = useNavigate()
  const dispatch = useDispatch()

  const handleEnroll = async () => {
    try {
      const orderResponse = await axios.post(
        `${BaseUrl}/api/payments/create_order/`,
        { course_id: course.id },
        { headers: { Authorization: `Bearer ${token}` } }
      )

      const orderData = orderResponse.data
      const options = {
        key: razorpay_key,
        amount: orderData.amount,
        currency: orderData.currency,
        name: course.name,
        description: course.description,
        order_id: orderData.order_id,
        handler: async function (response) {
          console.log("Payment response:", response)
          try {
            const verifyRes = await axios.post(
              `${BaseUrl}/api/payments/verify_payment/`,
              {
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                subscription_id: orderData.subscription_id
              },
              { headers: { Authorization: `Bearer ${token}` } }
            )

            toast.success("✅ Payment verified successfully!")
            dispatch(fetchCourses())
            setModal(false) 
            // navigate("/mycourses", { replace: true }) 
          } catch (error) {
            console.error("Verification error:", error)
            toast.error("❌ Payment verification failed")
          }
        },
        prefill: {
          name: "John Doe",
          email: "john@example.com",
          contact: "9999999999"
        },
        theme: { color: "#3399cc" }
      }

      const rzp = new window.Razorpay(options)
      rzp.open()
    } catch (error) {
      console.error("Enrollment error:", error)
      toast.error("Something went wrong. Try again.")
    }
  }

  return (
    <>
      <Card className="shadow-sm h-100 course-card">
        <CardImg
          top
          width="100%"
          height="200px"
          src={
            course.thumbnail ||
            "https://media.istockphoto.com/id/1353769234/photo/training-and-skill-development-concept-with-icons-of-online-course-conference-seminar-webinar.jpg?s=612x612&w=0&k=20&c=2YJG1My6Lu1T1FnzIPbimRNORcSbSuz6A8zb7HKNpx4="
          }
          alt={course.name}
        />
        <CardBody>
          <CardTitle tag="h5" className="fw-bold">
            {course.name}
          </CardTitle>
          <CardText className="text-muted">{course.description}</CardText>
          <div className="d-flex justify-content-between mt-2">
            <span>
              <FaClock className="me-1 text-secondary" />
              {course.duration_hours} hrs
            </span>
            <span>
              <FaChartLine className="text-primary me-1" />
              ₹{course.base_price}
            </span>
          </div>
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
          {course.name}
        </ModalHeader>
        <ModalBody className="course-modal-body">
          <p className="lead">{course.description}</p>

          <h6 className="fw-bold mt-3">Key Advantages:</h6>
          <ListGroup flush>
            {course.advantages?.map((adv, idx) => (
              <ListGroupItem
                key={idx}
                className="d-flex align-items-center border-0 px-0"
              >
                <FaCheckCircle className="text-success me-2" /> {adv}
              </ListGroupItem>
            ))}
          </ListGroup>

          <div className="mt-4 d-flex justify-content-between">
            <span>
              <FaClock className="me-2 text-secondary" />
              Duration: {course.duration_hours} hrs
            </span>
            <span>
              <FaChartLine className="me-2 text-primary" />
              Price: ₹{course.base_price}
            </span>
          </div>
        </ModalBody>
        <ModalFooter className="d-flex justify-content-between">
          <Button color="secondary" onClick={toggle}>
            Close
          </Button>
          <Button color="primary" onClick={handleEnroll}>
            Enroll Now
          </Button>
        </ModalFooter>
      </Modal>
    </>
  )
}

export default CourseCard
