import React, { Fragment, createContext, useReducer} from "react";
import Layout, { LayoutContext } from "../layout";
import { layoutReducer, layoutState } from "../layout/layoutContext";
import {  useNavigate } from "react-router-dom";
import main_bg from "../../images/main_bg.png"

import bg2 from "../../images/bg2.png"

// export const HomeContext  = createContext();

const HomeComponent = () => {
  const history = useNavigate();
  return (
    <Fragment>
      <div className="navber" style={{backgroundImage: `url(${main_bg})`,
        backgroundRepeat: "no-repeat",
        backgroundSize: "cover"}}>
        <div className="navber1">
          <div className="title">
            GDC <br/> Cognitive Platform
          </div>
          <div className="container">
            <button 
              onClick={(e) => history(`/trained`)}
              className="box"
            >
              Trained Model
            </button>
            <button 
              onClick={(e) => history(`/untrained`)}
              className="box"
            >
              Document<br/> Query Engine
            </button>
            <button
              onClick={(e) => history(`/configConverter`)}
              className="box"
            >
              Config Converter
            </button>
            <button
              onClick={(e) => history(`/crdGenerator`)}
              className="box"
            >
              CRD Generator
            </button>
          </div>
        </div>
      </div>
      
    </Fragment>
  );
};

const Home = (props) => {
  const [data, dispatch] = useReducer(layoutReducer, layoutState);
  return (
    <Fragment>
      <LayoutContext.Provider value={{ data, dispatch }}>
        <Layout children={<HomeComponent />} />
      </LayoutContext.Provider>
    </Fragment>
  );
};

export default Home;
