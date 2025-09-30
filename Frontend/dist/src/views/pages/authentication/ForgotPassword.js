// ** React Imports
import { Link, Navigate, useNavigate } from 'react-router-dom'

// ** Reactstrap Imports
import { Row, Col, CardTitle, CardText, Form, Label, Input, Button, FormFeedback } from 'reactstrap'

// ** Utils
import { isUserLoggedIn } from '@utils'

// ** Custom Hooks
import { useSkin } from '@hooks/useSkin'
import { useApiWithToast } from '@src/utility/hooks/useApiWithToast'

// ** Icons Imports
import { ChevronLeft } from 'react-feather'
import { useDispatch, useSelector } from 'react-redux'

// ** Illustrations Imports
import illustrationsLight from '@src/assets/images/pages/forgot-password-v2.svg'
import illustrationsDark from '@src/assets/images/pages/forgot-password-v2-dark.svg'

// ** Styles
import '@styles/react/pages/page-authentication.scss'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { forgotPassword, sendOtp, verifyOtp } from '../../../redux/authentication'
import UILoader from '@src/@core/components/ui-loader'
import themeConfig from '@configs/themeConfig'

const ForgotPassword = () => {
  // ** Hooks
  const { skin } = useSkin()
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [identifier, setIdentifier] = useState('')
  const [otp, setOtp] = useState('')
  const [otpVerified, setOtpVerified] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [errors, setErrors] = useState({})
  const { loading } = useSelector(state => state.auth)

  const source = skin === 'dark' ? illustrationsDark : illustrationsLight

  // ** API hooks with toast
  const { execute: executeSendOtp, loading: sendOtpLoading } = useApiWithToast(sendOtp, {
    onSuccess: (result) => {
      setStep(2)
    }
  })

  const { execute: executeVerifyOtp, loading: verifyOtpLoading } = useApiWithToast(verifyOtp, {
    onSuccess: (result) => {
      setOtpVerified(true)
      setStep(3)
    }
  })

  const { execute: executeForgotPassword, loading: forgotPasswordLoading } = useApiWithToast(forgotPassword, {
    onSuccess: (result) => {
      navigate("/login")
    }
  })

 const handleSendOtp = (e) => {
  e.preventDefault()
  console.log("fodd", identifier)
  setErrors({})

  if (!identifier.trim()) {
    setErrors({ identifier: "Please enter your email or phone number" })
    toast.error("Please enter your email or phone number")
    return
  }

  const isPhone = /^\d{10}$/.test(identifier)   // 10-digit phone
  const isEmail = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(identifier)

  if (!isPhone && !isEmail) {
    setErrors({ identifier: "Enter a valid email or phone number" })
    toast.error("Enter a valid email or phone number")
    return
  }

  const type = isPhone ? "phone" : "email"
  const finalIdentifier = isPhone ? `+91${identifier}` : identifier.trim()

  const payload = {
    identifier: finalIdentifier,
    identifier_type: type,
    purpose: "password_reset"
  }

  executeSendOtp(payload)
}


  // Step 2: Verify OTP
const handleVerifyOtp = (e) => {
  e.preventDefault()
  setErrors({})

  if (!otp.trim()) {
    setErrors({ otp: "Please enter OTP" })
    toast.error("Please enter OTP")
    return
  }

  const isPhone = /^\d{10}$/.test(identifier)
  const type = isPhone ? "phone" : "email"
  const finalIdentifier = isPhone ? `+91${identifier}` : identifier.trim()

  const payload = {
    identifier: finalIdentifier,
    identifier_type: type,
    otp_code: otp.trim(),
    purpose: "password_reset"
  }

  executeVerifyOtp(payload)
}


  // Step 3: Submit new password
const handleResetPassword = (e) => {
  e.preventDefault()

  if (!newPassword || !confirmPassword) {
    setErrors({ newPassword: "Enter new password", confirmPassword: "Confirm your password" })
    toast.error("Please fill all password fields")
    return
  }
  if (newPassword !== confirmPassword) {
    setErrors({ confirmPassword: "Passwords do not match" })
    toast.error("Passwords do not match")
    return
  }

  const isPhone = /^\d{10}$/.test(identifier)
  const type = isPhone ? "phone" : "email"
  const finalIdentifier = isPhone ? `+91${identifier}` : identifier.trim()

  const payload = {
    identifier: finalIdentifier,
    identifier_type: type,
    new_password: newPassword,
    confirm_password: confirmPassword,
    otp_code: otp.trim()
  }

  executeForgotPassword(payload)
}


  const isLoading = loading || sendOtpLoading || verifyOtpLoading || forgotPasswordLoading

  if (!isUserLoggedIn()) {
    return (
      <UILoader blocking={isLoading}>
        <div className='auth-wrapper auth-cover'>
        <Row className='auth-inner m-0'>
          {/* Logo */}
          <Link className='brand-logo' to='/' onClick={e => e.preventDefault()}>
          {/* <span className='brand-logo'> */}
              <img src={themeConfig.app.appLogoImage} alt='logo' height={30} width={30} />
            {/* </span> */}
          <h2 className='brand-text text-primary ms-1'>Edu Pravahaa</h2>
        </Link>

          {/* Illustration */}
          <Col className='d-none d-lg-flex align-items-center p-5' lg='8' sm='12'>
            <div className='w-100 d-lg-flex align-items-center justify-content-center px-5'>
              <img className='img-fluid' src={source} alt='Forgot Password Illustration' />
            </div>
          </Col>

          {/* Form */}
          <Col className='d-flex align-items-center auth-bg px-2 p-lg-5' lg='4' sm='12'>
            <Col className='px-xl-2 mx-auto' sm='8' md='6' lg='12'>
              <CardTitle tag='h2' className='fw-bold mb-1'>
                Forgot Password? 🔒
              </CardTitle>
              <CardText className='mb-2 text-muted text-start'>
                {step === 1 && "Enter your email or phone number and we'll send you an OTP"}
                {step === 2 && "Enter the OTP sent to your email or phone"}
                {step === 3 && "Set your new password"}
              </CardText>

              {/* Step 1 */}
              {step === 1 && (
                <Form className='mt-2' onSubmit={handleSendOtp}>
                  <div className='mb-3'>
                    <Label className='form-label' for='identifier'>Email or Phone</Label>
                    <Input
                      type='text'
                      id='identifier'
                      placeholder='Enter your Email or Phone'
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      invalid={!!errors.identifier}
                    />
                    {errors.identifier && <FormFeedback>{errors.identifier}</FormFeedback>}
                  </div>
                  <Button color='primary' block disabled={isLoading}>
                    {isLoading ? 'Sending...' : 'Send OTP'}
                  </Button>
                </Form>
              )}

              {/* Step 2 */}
              {step === 2 && (
                <Form className='mt-2' onSubmit={handleVerifyOtp}>
                  <div className='mb-3'>
                    <Label className='form-label' for='otp'>Enter OTP</Label>
                    <Input
                      type='text'
                      id='otp'
                      placeholder='Enter OTP'
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                      invalid={!!errors.otp}
                    />
                    {errors.otp && <FormFeedback>{errors.otp}</FormFeedback>}
                  </div>
                  <Button color='primary' block disabled={isLoading}>
                    {isLoading ? 'Verifying...' : 'Verify OTP'}
                  </Button>
                </Form>
              )}

              {/* Step 3 */}
              {step === 3 && (
                <Form className='mt-2' onSubmit={handleResetPassword}>
                  <div className='mb-3'>
                    <Label for='new-password'>New Password</Label>
                    <Input
                      type='password'
                      id='new-password'
                      placeholder='Enter new password'
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      invalid={!!errors.newPassword}
                    />
                    {errors.newPassword && <FormFeedback>{errors.newPassword}</FormFeedback>}
                  </div>
                  <div className='mb-3'>
                    <Label for='confirm-password'>Confirm Password</Label>
                    <Input
                      type='password'
                      id='confirm-password'
                      placeholder='Confirm new password'
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      invalid={!!errors.confirmPassword}
                    />
                    {errors.confirmPassword && <FormFeedback>{errors.confirmPassword}</FormFeedback>}
                  </div>
                  <Button color='primary' block disabled={isLoading}>
                    {isLoading ? 'Resetting...' : 'Submit'}
                  </Button>
                </Form>
              )}

              {/* Back to login */}
              <p className='text-center mt-2'>
                <Link to='/login'>
                  <ChevronLeft className='rotate-rtl me-25' size={14} />
                  <span className='align-middle'>Back to login</span>
                </Link>
              </p>
            </Col>
          </Col>
        </Row>
        </div>
      </UILoader>
    )
  } else {
    return <Navigate to='/' />
  }
}

export default ForgotPassword
