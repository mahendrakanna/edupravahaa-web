// ** React Imports
import { useContext, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

// ** Custom Hooks
import { useSkin } from '@hooks/useSkin'
import useJwt from '@src/auth/jwt/useJwt'

// ** Store & Actions
import { useDispatch, useSelector } from 'react-redux'


// ** Third Party Components
import { useForm, Controller } from 'react-hook-form'
import {CheckCircle } from 'react-feather'

// ** Context
import { AbilityContext } from '@src/utility/context/Can'

// ** Custom Components
import InputPasswordToggle from '@components/input-password-toggle'

// ** Reactstrap Imports
import {
  Row,
  Col,
  Form,
  Label,
  Input,
  Button,
  CardTitle,
  FormFeedback,
  Spinner,
 
} from "reactstrap"

// ** Illustrations Imports
import illustrationsLight from '@src/assets/images/pages/register-v2.svg'
import illustrationsDark from '@src/assets/images/pages/register-v2-dark.svg'

// ** Styles
import '@styles/react/pages/page-authentication.scss'
import {  sendOtp,signupUser,verifyOtp } from '../../../redux/authentication'
import toast from 'react-hot-toast'

const defaultValues = {
  email: '',
  terms: false,
  username: '',
  password: '',
  phone: '',            
  confirmpassword: ''
}

const Register = () => {
  // ** Hooks
  const ability = useContext(AbilityContext)
  const { skin } = useSkin()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const {
    control,
    setError,
    handleSubmit,
    getValues,
    watch,  
    formState: { errors }
  } = useForm({ defaultValues })

  const [otpType, setOtpType] = useState("")
  const [otpValue, setOtpValue] = useState("")
  const [otp, setOtp] = useState("")
  const [isEmailVerified, setIsEmailVerified] = useState(false);
  const [isPhoneVerified, setIsPhoneVerified] = useState(false);
  const [otpSentSuccess, setOtpSentSuccess] = useState(false);
  const { loading } = useSelector(state => state.auth)

  console.log("errors", errors)

  const source = skin === 'dark' ? illustrationsDark : illustrationsLight

  const watchedEmail = watch("email")
  const watchedPhone = watch("phone")
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const phonePattern = /^[0-9]{10}$/

const isEmailValid = emailPattern.test(watchedEmail)
const isPhoneValid = phonePattern.test(watchedPhone)
  const onSubmit = data => {
    console.log("Submitted Data:", data)
    const tempData = { ...data }
    delete tempData.terms
    if (!isEmailVerified) {
      setError("email", { type: "manual", message: "Please verify your email" });
      return;
    }
    if (!isPhoneVerified) {
      setError("phone", { type: "manual", message: "Please verify your phone number" });
      return;
    }
    if (Object.values(tempData).every(field => field.length > 0) && data.terms === true) {
      const payload = {
        username: data.username,
        email: data.email,
        password: data.password,
        confirm_password: data.confirmpassword,
        phone_number: `+91${data?.phone}`,
      }
      dispatch(signupUser(payload))
      .unwrap()
      .then((res) => {
      toast.success(res.message || "Registration successful");
        navigate('/login')
      })
      .catch(err => console.log(err))
    } else {
      for (const key in data) {
        if (data[key].length === 0) {
          setError(key, {
            type: 'manual',
            message: `Please enter a valid ${key}`
          })
        }
        if (key === 'terms' && data.terms === false) {
          setError('terms', {
            type: 'manual'
          })
        }
      }
    }
  }

   const handleSendOtp = (type, value) => {
    if (!value) {
      alert(`Please enter ${type} first`);
      return;
    }
    let otpValue = value 
      if (type === "phone") {
        otpValue = `+91${otpValue}`
      }
    const payload = {
      identifier: otpValue,
      identifier_type: type,
      purpose: "registration",
    };
    setOtpType(type);
    setOtpValue(value);
    dispatch(sendOtp(payload))
    .unwrap()
    .then(res => {
      // Show OTP sent message from backend
      toast.success(res.message || `OTP sent to your ${type}`)
      setOtpSentSuccess(true)
    })
    .catch(err => {
      toast.error(err.error || `Failed to send OTP`)
      setOtpSentSuccess(false)
    })
  };

  const handleVerifyOtp = () => {
    let value = otpValue 
  if (otpType === "phone") {
    value = `+91${otpValue}`
  }

  const payload = {
    identifier: value,
    identifier_type: otpType,
    otp_code: otp,
    purpose: "registration",
  }
  dispatch(verifyOtp(payload))
    .unwrap()
    .then(res => {
      // Show success message from backend
      toast.success(res.message || `${otpType} verified successfully`)

      if (otpType === "email") setIsEmailVerified(true)
      if (otpType === "phone") setIsPhoneVerified(true)

      // Reset OTP state
      setOtp("")
      setOtpType("")
      setOtpValue("")
      setOtpSentSuccess(false)
    })
    .catch(err => {
      // Show error
      toast.error(err.error || "Invalid OTP")
    })
  }
  console.log("loading:", loading)
  return (
 <div className="auth-wrapper auth-cover">
      <Row className="auth-inner m-0">
        <Col className="d-none d-lg-flex align-items-center p-5" lg="8" sm="12">
          <div className="w-100 d-lg-flex align-items-center justify-content-center px-5">
            <img className="img-fluid" src={source} alt="Register Cover" />
          </div>
        </Col>
        <Col className="d-flex align-items-center auth-bg px-2 p-lg-5" lg="4" sm="12">
          <Col className="px-xl-2 mx-auto" sm="8" md="6" lg="12">
            <CardTitle tag="h2" className="fw-bold mb-1">
              Start Your Journey 🚀
            </CardTitle>

            <Form className="auth-register-form mt-2" onSubmit={handleSubmit(onSubmit)}>
              {/* Username */}
              <div className="mb-1">
                <Label className="form-label" for="username">Username</Label>
                <Controller
                  name="username"
                  control={control}
                  rules={{ required: "Username is required" }}
                  render={({ field }) => (
                    <Input
                      placeholder="johndoe"
                      invalid={!!errors.username}
                      {...field}
                    />
                  )}
                />
                {/* {errors.username && <FormFeedback>{errors.username.message}</FormFeedback>} */}
              </div>

              {/* Email with Verify + OTP */}
              <div className="mb-1">
                <Label className="form-label" for="email">Email</Label>
                <div className="position-relative">
                  {/* Email */}
              <Controller
                name="email"
                control={control}
                rules={{
                  required: "Email is required",
                  pattern: {
                    value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                    message: "Enter a valid email address"
                  }
                }}
                render={({ field }) => (
                  <Input
                    type="email"
                    id="email"
                    placeholder="john@example.com"
                    invalid={!!errors.email}
                    {...field}
                    style={{ paddingRight: "90px" }}
                  />
                )}
              />
            {isEmailVerified ? (
                <CheckCircle
                  color="green"
                  size={22}
                  className="position-absolute top-50 end-0 translate-middle-y me-1"
                  style={{ right: "10px", pointerEvents: "none" }}
                />
              ) : (
                <Button
                    type="button"
                    color="link"
                    disabled={!isEmailValid || loading}
                    className="position-absolute top-50 end-0 translate-middle-y me-1"
                    onClick={() => handleSendOtp("email", watchedEmail)}
                  >
                    {loading ? <Spinner size="sm" /> : "Verify"}
                  </Button>
              )}
                {/* {errors.email && <FormFeedback>{errors.email.message}</FormFeedback>} */}

                </div>
              {otpType === "email" && otpSentSuccess && (
              <div className="input-group mt-1">
                <Input
                  type="text"
                  placeholder="Enter OTP"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value)}
                />
               <Button 
                  color="primary" 
                  onClick={handleVerifyOtp}
                  disabled={loading} 
                >
                  {loading ? <Spinner size="sm" /> : "Verify OTP"}
                </Button>
              </div>
            )}

              </div>
              <div className="mb-1">
                <Label className="form-label" for="phone">Phone</Label>
                
              <div className="position-relative">
                <Controller
                  name="phone"
                  control={control}
                  rules={{
                    required: "Phone number is required",
                    pattern: {
                      value: /^[0-9]{10}$/,
                      message: "Enter a valid 10-digit phone number"
                    }
                  }}
                  render={({ field }) => (
                    <Input
                      type="tel"
                      id="phone"
                      placeholder="123567890"
                      invalid={!!errors.phone}
                      {...field}
                      style={{ paddingRight: "90px" }}
                    />
                  )}
                />
                {isPhoneVerified ? (
                  <CheckCircle
                    color="green"
                    size={22}
                    className="position-absolute top-50 end-0 translate-middle-y me-1"
                    style={{ right: "10px", pointerEvents: "none" }}
                  />
                ) : (
                  <Button
                    type="button"
                    color="link"
                    disabled={!isPhoneValid}
                    className="position-absolute top-50 end-0 translate-middle-y me-1"
                    onClick={() => handleSendOtp("phone", watchedPhone)}
                  >
                    Verify
                  </Button>
                )}
                {/* {errors.phone && <FormFeedback>{errors.phone.message}</FormFeedback>} */}
              </div>

                {/* OTP field shown only after sending OTP */}
                {otpType === "phone" && otpSentSuccess && (
                  <div className="mt-1 d-flex">
                    <Input
                      type="text"
                      placeholder="Enter OTP"
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                    />
                    <Button 
                      color="primary" 
                      className="ms-1" 
                      onClick={handleVerifyOtp}
                      disabled={loading}
                    >
                      {loading ? <Spinner size="sm" /> : "Submit"}
                    </Button>
                  </div>
                )}
              </div>

              {/* Password */}
              <div className="mb-1">
                <Label className="form-label" for="password">Password</Label>
                <Controller
                  name="password"
                  control={control}
                  rules={{ required: "Password is required" }}
                  render={({ field }) => (
                    <InputPasswordToggle
                      className="input-group-merge"
                      invalid={!!errors.password}
                      {...field}
                    />
                  )}
                />
                {/* {errors.password && <FormFeedback>{errors.password.message}</FormFeedback>} */}
              </div>

              {/* Confirm Password */}
              <div className="mb-1">
                <Label className="form-label" for="confirmpassword">Confirm Password</Label>
                <Controller
                  name="confirmpassword"
                  control={control}
                  rules={{
                    required: "Please confirm your password",
                    validate: (value) =>
                      value === getValues("password") || "Passwords do not match"
                  }}
                  render={({ field }) => (
                    <Input
                      type="password"
                      placeholder="Confirm Password"
                      invalid={!!errors.confirmpassword}
                      {...field}
                    />
                  )}
                />
                {/* {errors.confirmpassword && <FormFeedback>{errors.confirmpassword.message}</FormFeedback>} */}
              </div>

              {/* Terms */}
              <div className="form-check mb-1">
                <Controller
                  name="terms"
                  control={control}
                  rules={{ required: "You must agree to terms" }}
                  render={({ field }) => (
                    <Input
                      {...field}
                      id="terms"
                      type="checkbox"
                      checked={field.value}
                      invalid={!!errors.terms}
                    />
                  )}
                />
                <Label className="form-check-label" for="terms">
                  I agree to <a href="/" onClick={(e) => e.preventDefault()}>privacy policy & terms</a>
                </Label>
                {errors.terms && <FormFeedback>{errors.terms.message}</FormFeedback>}
              </div>

              <Button type="submit" block color="primary">Sign up</Button>
            </Form>



            <p className="text-center mt-2">
              <span className="me-25">Already have an account?</span>
              <Link to="/login"><span>Sign in instead</span></Link>
            </p>
          </Col>
        </Col>
      </Row>
    </div>
  )
}

export default Register
