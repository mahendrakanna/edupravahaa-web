import { Fragment, useState, useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import {
  Row,
  Col,
  Card,
  CardHeader,
  CardBody,
  Form,
  FormGroup,
  Label,
  Input,
  Button,
  Modal,
  ModalHeader,
  ModalBody,
  ModalFooter,
  Alert,
  Badge
} from 'reactstrap';

import UILoader from '@components/ui-loader';
import InputPasswordToggle from '@components/input-password-toggle'
import Breadcrumbs from '@components/breadcrumbs';

// Icons
import { 
  Mail, 
  Phone, 
  User, 
  Calendar, 
  Edit3, 
  Save,
  X,
  Shield,
  CheckCircle,
  Clock,
  Key
} from 'react-feather';


import { verifyOtp, updatePassword, sendOtp, updateProfile, getProfile } from '../../../redux/authentication';
import toast from 'react-hot-toast';
import "../../../@core/scss/base/pages/app-profile.scss"
import { Controller, get, useForm } from 'react-hook-form';

const Profile = () => {
  const dispatch = useDispatch();
  const user = useSelector(state => state.auth.user);
const {
  control,
  handleSubmit,
  watch,
  formState: { errors }
} = useForm({
  defaultValues: {
    old_password: "",
    new_password: "",
    confirm_password: ""
  }
});

  // States
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState({});
  const [otpModal, setOtpModal] = useState(false);
  const [otpData, setOtpData] = useState({ type: '', value: '', otp: '' });
  const [loading, setLoading] = useState(false);
  const [alert, setAlert] = useState({ visible: false, message: '', color: '' });
  const [showPasswordUpdate, setShowPasswordUpdate] = useState(false);
  const [photo, setPhoto] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const [emailVerified, setEmailVerified] = useState(user?.email_verified || false);
  const [phoneVerified, setPhoneVerified] = useState(user?.phone_verified || false);
  
  // OTP states
  const [otpType, setOtpType] = useState('');
  const [otpValue, setOtpValue] = useState('');
  const [otp, setOtp] = useState('');
  const [otpSentSuccess, setOtpSentSuccess] = useState(false);
  
  // Password update states
  const [passwordData, setPasswordData] = useState({
    old_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [passwordLoading, setPasswordLoading] = useState(false);

  // Initialize form data with user data
  useEffect(() => {
    if (user) {
      setFormData({
        first_name: user.first_name || '',
        last_name: user.last_name || '',
        username: user.username || '',
        email: user.email || '',
        phone_number: user.phone_number || ''
      });
      setEmailVerified(user.email_verified || false);
      setPhoneVerified(user.phone_verified || false);
      setPhotoPreview(user.profile || null);
      setPhoto(null);
    }
  }, [user]);

  // Handle input changes
  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle password input changes
  const handlePasswordChange = (e) => {
    const { name, value } = e.target;
    setPasswordData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  // Handle photo upload
  const handlePhotoChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      // Check file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        toast.error('Image size should be less than 5MB');
        return;
      }
      
      // Check file type
      if (!file.type.startsWith('image/')) {
        toast.error('Please select an image file');
        return;
      }
      
      setPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
    }
  };

  // Handle send OTP
  const handleSendOtp = (type, value) => {
    if (!value) {
      toast.error(`Please enter ${type} first`);
      return;
    }
    
    let otpValue = value;
    if (type === "phone") {
      otpValue = otpValue;
    }
    
    const payload = {
      identifier: otpValue,
      identifier_type: type,
      purpose: "profile_update",
    };
    
    setOtpType(type);
    setOtpValue(value);
    
    dispatch(sendOtp(payload))
      .unwrap()
      .then(res => {
        // Show OTP sent message from backend
        toast.success(res.message || `OTP sent to your ${type}`);
        setOtpSentSuccess(true);
        setOtpModal(true);
      })
      .catch(err => {
        toast.error(err.error || `Failed to send OTP`);
        setOtpSentSuccess(false);
      });
  };

  // Handle OTP verification
  const handleVerifyOtp = () => {
    let value = otpValue;
    if (otpType === "phone") {
      value = otpValue;
    }

    const payload = {
      identifier: value,
      // identifier_type: otpType,
      otp_code: otp,
      purpose: "profile_update",
    };
    
    dispatch(updateProfile(payload))
      .unwrap()
      .then(res => {
        // Show success message from backend
        toast.success(res.message || `${otpType} verified successfully`);

        if (otpType === "email") setEmailVerified(true);
        if (otpType === "phone") setPhoneVerified(true);

        // Reset OTP state
        setOtp("");
        setOtpType("");
        setOtpValue("");
        setOtpSentSuccess(false);
        setOtpModal(false);
      })
      .catch(err => {
        // Show error
        toast.error(err.error || "Invalid OTP");
      });
  };

  // Handle profile update
  const handleProfileUpdate = async () => {
    setLoading(true);

    try {
      const formDataToSend = new FormData();
      
      // Add changed text fields
      Object.keys(formData).forEach(key => {
        if (formData[key] !== user[key]) {
          formDataToSend.append(key, formData[key]);
        }
      });

      console.log("photo",photo,"photoPreview",photoPreview)
          // Add profile image if selected
      if (photo) {
        formDataToSend.append('profile_picture', photo);
      }
      
      // Check if there's any data to update
      if (formDataToSend.entries().next().done && !photo) {
        toast.info('No changes to update');
        setLoading(false);
        return;
      }
      
      const result = await dispatch(updateProfile(formDataToSend)).unwrap();
      
      toast.success(result.message || 'Profile updated successfully!');
      dispatch(getProfile());
      setEditMode(false);
      
      // Reset photo state after successful update
      if (photo) {
        setPhoto(null);
      }
    } catch (error) {
      toast.error(error.error || 'Failed to update profile');
    } finally {
      setLoading(false);
    }
  };

  // Handle form submit
  const handleSubmit1 = async (e) => {
    e.preventDefault();
    
    // Check if email or phone has changed and needs verification
    const emailChanged = formData.email !== user?.email;
    const phoneChanged = formData.phone_number !== user?.phone_number;
    
    if (emailChanged && !emailVerified) {
      toast.error('Please verify your new email address first');
      return;
    }
    
    if (phoneChanged && !phoneVerified) {
      toast.error('Please verify your new phone number first');
      return;
    }
    
    handleProfileUpdate();
  };

  // Handle password update
 const handlePasswordUpdate = async (data) => {
  if (data.new_password !== data.confirm_password) {
    toast.error("New passwords do not match");
    return;
  }

  setPasswordLoading(true);

  try {
    const result = await dispatch(updatePassword(data)).unwrap();
    toast.success(result.message || "Password updated successfully!");
    setShowPasswordUpdate(false);
  } catch (error) {
    toast.error(error.message || "Failed to update password");
  } finally {
    setPasswordLoading(false);
  }
};

  // Format date
  const formatDate = (dateString) => {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
  };

  // Get user initials for avatar
  const getUserInitials = () => {
    if (user?.first_name && user?.last_name) {
      return `${user.first_name[0]}${user.last_name[0]}`.toUpperCase();
    } else if (user?.username) {
      return user.username.substring(0, 2).toUpperCase();
    }
    return 'US';
  };

  // Check if email/phone is changed
  const isEmailChanged = formData.email !== user?.email;
  const isPhoneChanged = formData.phone_number !== user?.phone_number;

  return (
    <Fragment>
      <Breadcrumbs title='Profile' data={[{ title: 'Pages' }, { title: 'Profile' }]} />

      {alert.visible && (
        <Alert color={alert.color} className="position-fixed top-0 end-0 m-3 z-index-1050">
          {alert.message}
        </Alert>
      )}

      <div id='user-profile'>
        <Row>
          <Col lg="4" md="5">
            {/* Profile Card */}
            <Card className="profile-card pt-2">
              <CardBody className="text-center">
                <div className="profile-avatar">
                  <div className="avatar-initials">
                     { user.profile_picture ?
                     <img src={user.profile_picture} alt="Profile" style={{ width: '100px', height: '100px', borderRadius: '50%', objectFit: 'cover' }} />
                     : (
                      getUserInitials()
                    )}

                    {/* {photoPreview && (
                      <img src={photoPreview} alt="Profile" style={{ width: '100px', height: '100px', borderRadius: '50%', objectFit: 'cover' }} />
                    ) } */}
                  </div>
                </div>
                <h4 className="profile-name">{user?.username}</h4>
                <Badge color="primary" className="profile-role">{user?.role}</Badge>
                <div className="profile-stats">
                  <div className="stat-item">
                    <CheckCircle size={18} className="text-success" />
                    <span>Verified Profile</span>
                  </div>
                  <div className="stat-item">
                    <Calendar size={18} className="text-primary" />
                    <span>Joined {formatDate(user?.date_joined)}</span>
                  </div>
                </div>
              </CardBody>
            </Card>

            {/* Quick Actions Card */}
            <Card className="profile-actions">
              <CardHeader>
                <h5>Quick Actions</h5>
              </CardHeader>
              <CardBody>
                <Button color="outline-secondary" className="w-100 mb-2" onClick={() => setShowPasswordUpdate(true)}>
                  <Key size={16} className="me-1" />
                  Update Password
                </Button>
                {!editMode ? (
                  <Button color="outline-primary" className="w-100" onClick={() => setEditMode(true)}>
                    <Edit3 size={16} className="me-1" />
                    Edit Profile
                  </Button>
                ) : (
                  <Button color="outline-secondary" className="w-100" onClick={() => setEditMode(false)}>
                    <X size={16} className="me-1" />
                    Cancel Edit
                  </Button>
                )}
              </CardBody>
            </Card>
          </Col>

          <Col lg="8" md="7">
            {/* Profile Information Card */}
            <Card>
              <CardHeader className="d-flex justify-content-between align-items-center">
                <h5>Profile Information</h5>
                {!editMode && (
                  <Button color="primary" outline onClick={() => setEditMode(true)}>
                    <Edit3 size={14} className="me-1" />
                    Edit
                  </Button>
                )}
              </CardHeader>
              <CardBody>
                {!editMode ? (
                  // View Mode
                  <div className="profile-info">
                    <div className="info-item">
                      <User size={18} className="text-primary me-2" />
                      <div>
                        <div className="info-label">User Name</div>
                        <div className="info-value">{user?.username || 'Not provided'}</div>
                      </div>
                    </div>
                    <div className="info-item">
                      <Mail size={18} className="text-primary me-2" />
                      <div>
                        <div className="info-label">Email Address</div>
                        <div className="info-value d-flex align-items-center">
                          {user?.email}
                          {emailVerified && (
                            <Badge color="success" className="ms-2">
                              <CheckCircle size={12} className="me-1" />
                              Verified
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="info-item">
                      <Phone size={18} className="text-primary me-2" />
                      <div>
                        <div className="info-label">Phone Number</div>
                        <div className="info-value d-flex align-items-center">
                          {user?.phone_number}
                          {phoneVerified && (
                            <Badge color="success" className="ms-2">
                              <CheckCircle size={12} className="me-1" />
                              Verified
                            </Badge>
                          )}
                        </div>
                      </div>
                    </div>
                    <div className="info-item">
                      <Calendar size={18} className="text-primary me-2" />
                      <div>
                        <div className="info-label">Member Since</div>
                        <div className="info-value">{formatDate(user?.date_joined)}</div>
                      </div>
                    </div>
                  </div>
                ) : (
                  // Edit Mode
                  <Form onSubmit={handleSubmit1}>
                    {/* Upload Photo */}
                    <FormGroup>
                      <Label for="photo">Profile Photo</Label>
                      <Input
                        type="file"
                        name="photo"
                        id="photo"
                        accept="image/*"
                        onChange={handlePhotoChange}
                      />
                      {photoPreview && (
                        <div className="mt-2">
                          <img 
                            src={photoPreview} 
                            alt="Preview" 
                            style={{ width: '80px', height: '80px', borderRadius: '50%', objectFit: 'cover' }} 
                          />
                          <small className="d-block text-muted mt-1">
                            {photo ? 'New image selected' : 'Current profile image'}
                          </small>
                        </div>
                      )}
                    </FormGroup>
                    <FormGroup>
                      <Label for="username">Username</Label>
                      <Input
                        type="text"
                        name="username"
                        id="username"
                        value={formData.username}
                        onChange={handleInputChange}
                        placeholder="Enter username"
                      />
                    </FormGroup>
                    <FormGroup>
                      <Label for="email">
                        Email Address
                        {emailVerified && (
                          <Badge color="success" className="ms-1">Verified</Badge>
                        )}
                      </Label>
                      <div className="d-flex">
                        <Input
                          type="email"
                          name="email"
                          id="email"
                          value={formData.email}
                          onChange={handleInputChange}
                          placeholder="Enter email address"
                          disabled={emailVerified}
                        />
                        {/* <Button 
                          color="outline-primary" 
                          className="ms-2"
                          onClick={() => handleSendOtp('email', formData.email)}
                          disabled={!isEmailChanged || emailVerified}
                        >
                          {isEmailChanged && !emailVerified ? 'Verify' : 'Update'}
                        </Button> */}
                      </div>
                    </FormGroup>
                    <FormGroup>
                      <Label for="phone_number">
                        Phone Number
                        {phoneVerified && (
                          <Badge color="success" className="ms-1">Verified</Badge>
                        )}
                      </Label>
                      <div className="d-flex">
                        <Input
                          type="tel"
                          name="phone_number"
                          id="phone_number"
                          value={formData.phone_number}
                          onChange={handleInputChange}
                          placeholder="Enter phone number"
                         
                        />
                        <Button 
                          color="outline-primary" 
                          className="ms-2"
                          onClick={() => handleSendOtp('phone', formData.phone_number)}
                          disabled={!isPhoneChanged}
                        >
                          {isPhoneChanged && !phoneVerified ? 'Verify' : 'Update'}
                        </Button>
                      </div>
                    </FormGroup>
                    <div className="d-flex mt-4">
                      <Button color="primary" type="submit" className="me-2" disabled={loading}>
                        {loading ? (
                          <>
                            <span className="spinner-border spinner-border-sm me-1" />
                            Saving...
                          </>
                        ) : (
                          <>
                            <Save size={16} className="me-1" />
                            Save Changes
                          </>
                        )}
                      </Button>
                      <Button color="outline-secondary" onClick={() => setEditMode(false)} disabled={loading}>
                        <X size={16} className="me-1" />
                        Cancel
                      </Button>
                    </div>
                  </Form>
                )}
              </CardBody>
            </Card>
          </Col>
        </Row>
      </div>

      {/* OTP Verification Modal */}
      <Modal isOpen={otpModal} toggle={() => setOtpModal(!otpModal)} className="modal-dialog-centered">
        <ModalHeader toggle={() => setOtpModal(!otpModal)}>
          Verify OTP
        </ModalHeader>
        <ModalBody>
          <div className="text-center mb-3">
            <div className="otp-icon bg-light-primary">
              <Shield size={30} className="text-primary" />
            </div>
            <h5>Enter Verification Code</h5>
            <p className="text-muted">
              Please enter the 4-digit verification code sent to your {otpType}
            </p>
          </div>
          <FormGroup>
            <Label for="otp">Verification Code</Label>
            <Input
              type="text"
              name="otp"
              id="otp"
              placeholder="Enter 4-digit code"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
              maxLength="4"
              className="text-center otp-input"
            />
          </FormGroup>
          <div className="text-center text-muted mt-3">
            Didn't receive the code? <a href="#" onClick={() => handleSendOtp(otpType, otpValue)}>Resend</a>
          </div>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={() => setOtpModal(false)} disabled={loading}>
            Cancel
          </Button>
          <Button color="primary" onClick={handleVerifyOtp} disabled={loading || otp.length !== 4}>
            {loading ? (
              <>
                <span className="spinner-border spinner-border-sm me-1" />
                Verifying...
              </>
            ) : (
              'Verify Code'
            )}
          </Button>
        </ModalFooter>
      </Modal>

      {/* Password Update Modal */}
      <Modal isOpen={showPasswordUpdate} toggle={() => setShowPasswordUpdate(!showPasswordUpdate)} className="modal-dialog-centered">
        <ModalHeader toggle={() => setShowPasswordUpdate(false)}>
          Update Password
        </ModalHeader>
       <Form onSubmit={handleSubmit(handlePasswordUpdate)}>
        <ModalBody>
          <FormGroup>
            <Label for="old_password">Current Password</Label>
            <Controller
              name="old_password"
              control={control}
              rules={{ required: "Old password is required" }}
              render={({ field }) => (
                <InputPasswordToggle
                  className="input-group-merge"
                  invalid={errors.old_password && true}
                  {...field}
                />
              )}
            />
          </FormGroup>

          <FormGroup>
            <Label for="new_password">New Password</Label>
            <Controller
              name="new_password"
              control={control}
              rules={{ required: "New password is required" }}
              render={({ field }) => (
                <InputPasswordToggle
                  className="input-group-merge"
                  invalid={errors.new_password && true}
                  {...field}
                />
              )}
            />
          </FormGroup>

          <FormGroup>
            <Label for="confirm_password">Confirm New Password</Label>
            <Controller
              name="confirm_password"
              control={control}
              rules={{ required: "Confirm password is required" }}
              render={({ field }) => (
                <InputPasswordToggle
                  className="input-group-merge"
                  invalid={errors.confirm_password && true}
                  {...field}
                />
              )}
            />
          </FormGroup>
        </ModalBody>
        <ModalFooter>
          <Button color="secondary" onClick={() => setShowPasswordUpdate(false)} disabled={passwordLoading}>
            Cancel
          </Button>
          <Button color="primary" type="submit" disabled={passwordLoading}>
            {passwordLoading ? (
              <>
                <span className="spinner-border spinner-border-sm me-1" />
                Updating...
              </>
            ) : (
              "Update Password"
            )}
          </Button>
        </ModalFooter>
      </Form>

      </Modal>

    </Fragment>
  );
};

export default Profile;