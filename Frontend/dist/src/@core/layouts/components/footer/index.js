// ** Icons Import
import { Heart } from 'react-feather'

const Footer = () => {
  return (
    <p className='clearfix mb-0'>
      <span className='float-md-start d-block d-md-inline-block mt-25'>
        COPYRIGHT © {new Date().getFullYear()}{' '}
        <a href='' target='_blank' rel='noopener noreferrer'>
          Edu Pravahaa
        </a>
        <span className='d-none d-sm-inline-block'>, All rights Reserved</span>
      </span>
      <span className='float-md-end d-none d-md-block'>
        Hand-crafted & Made with
        <Heart size={14} />
      </span>
    </p>
  )
}

export default Footer


// Footer.jsx
import React from "react";
// import { Facebook, Twitter, Youtube, Linkedin, Heart } from "react-feather";
// import logo from "../../../../assets/images/logo/SBlogo.png"; 

// const Footer = () => {
//   const year = new Date().getFullYear();

//   return (
//     <footer className="bg-light text-dark pt-5 border-top">
//       <div className="container">
//         <div className="row">

//           <div className="col-md-4 mb-4">
//             <div className="d-flex align-items-center mb-3">
//               <img src={logo} alt="Logo" width="40" height="40" className="me-2" />
//               <h5 className="mb-0">StudentBook</h5>
//             </div>
//             <p>Empowering students with knowledge and tools for a brighter future.</p>
//             <div className="d-flex gap-3 mt-3">
//               <Facebook size={18} />
//               <Twitter size={18} />
//               <Youtube size={18} />
//               <Linkedin size={18} />
//             </div>
//           </div>

//           <div className="col-md-2 mb-4">
//             <h6>Explore</h6>
//             <ul className="list-unstyled">
//               <li><a href="#">About Us</a></li>
//               <li><a href="#">Success Stories</a></li>
//               <li><a href="#">Careers</a></li>
//               <li><a href="#">Resource Center</a></li>
//               <li><a href="#">Courses</a></li>
//               <li><a href="#">Contact Us</a></li>
//             </ul>
//           </div>

//           <div className="col-md-3 mb-4">
//             <h6>Categories</h6>
//             <ul className="list-unstyled">
//               <li><a href="#">All Courses</a></li>
//               <li><a href="#">Voice & Storytelling</a></li>
//               <li><a href="#">Digital Marketing</a></li>
//               <li><a href="#">Design & Branding</a></li>
//               <li><a href="#">Nanodegree</a></li>
//               <li><a href="#">Veterans</a></li>
//             </ul>
//           </div>

//           <div className="col-md-3 mb-4">
//             <h6>Support</h6>
//             <ul className="list-unstyled">
//               <li><a href="#">Help Center</a></li>
//               <li><a href="#">System Requirements</a></li>
//               <li><a href="#">Activation Key</a></li>
//               <li><a href="#">Site Feedback</a></li>
//               <li><a href="#">Documentation</a></li>
//               <li><a href="#">Forums</a></li>
//             </ul>
//           </div>
//         </div>

//         <div className="border-top pt-3 text-center">
//           <p className="mb-0">
//             © {year} All Rights Reserved | Design by <a href="#">StudentBook Team</a>
//           </p>
//           <p className="mt-1">
//             Hand-crafted & Made with <Heart size={14} className="text-danger" />
//           </p>
//         </div>
//       </div>
//     </footer>
//   );
// };

// export default Footer;
