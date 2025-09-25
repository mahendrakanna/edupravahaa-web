import { Container, Row, Col } from "reactstrap"
import TeacherDashboard from "./teacherDashboard"

const EcommerceDashboard = () => {
  return(
    <Container>
      <Row>
        <Col md="12">
          <TeacherDashboard />
        </Col>
      </Row>
    </Container>
  )
}
export default EcommerceDashboard;
