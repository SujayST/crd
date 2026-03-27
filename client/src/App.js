import React, { Fragment, useReducer} from "react";
import { LayoutContext } from "./components/layout";
import { layoutReducer, layoutState } from "./components/layout/layoutContext";
import Routes1 from "./components";


function App() {
  const [data, dispatch] = useReducer(layoutReducer, layoutState);
  return (
    <Fragment>
      <LayoutContext.Provider value={{ data, dispatch }}>
        <Routes1 />
      </LayoutContext.Provider>   
    </Fragment>
  );
}

export default App;
