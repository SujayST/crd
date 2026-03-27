import React, { Fragment, createContext} from "react";
import "./style.css";
import Navbar from "../partials/Navbar";
import Footer from "../partials/Footer";


export const LayoutContext = createContext();

const Layout = ({ children }) => {
  return (
    <Fragment>
      <div className="wrapper">
        <Navbar />
        {/* All Children pass from here */}
        
        {children}
      </div>
      <Footer />
    </Fragment>
  );
};

export default Layout;



