import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import PageNotFound from "./layout/PageNotFound";
import Home from "./home";
import Trained from "./home/trained";
import Untrained from "./home/untrained";
import ConfigConverter from "./home/configconverter";
import CrdGenerator from "./home/CrdGenerator";

/* Routing All page will be here */
const Routes1 = (props) => {
  return (
    <Router history={window.history} >
      <Routes>
        {/* Public Routes */}
        <Route exact path="/" element={<Home/>} />
        {/* 404 Page */}
        <Route path="/trained" element={<Trained/>}/>
        <Route path="/untrained" element={<Untrained/>}/>
        <Route path="/configconverter" element={<ConfigConverter/>}/>
        <Route path="/crdGenerator" element={<CrdGenerator/>}/>
        <Route element={<PageNotFound/>} />
      </Routes>
    </Router>
  );
};

export default Routes1;
