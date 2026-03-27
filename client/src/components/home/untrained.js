import { Fragment, useEffect, useReducer, useRef, useState } from "react";
import { layoutReducer, layoutState } from "../layout/layoutContext";
import Layout, { LayoutContext } from "../layout";
import Button from '@mui/material/Button';
import SendIcon from '@mui/icons-material/Send';
import "./style.css";
import axios from "axios";
// import styled from "@emotion/styled";
import LinearProgress from '@mui/material/LinearProgress';
import ScrollToBottom from 'react-scroll-to-bottom';
import Box from '@mui/material/Box';
import bg2 from "../../images/bg2.png"
import { getVectorStores } from "./FetchApi";
import AddCircleIcon from '@mui/icons-material/AddCircle';
const apiURL = process.env.REACT_APP_API_URL;

const UntrainedComponent = () => {
  const [data, setData] = useState({
    query: "",
  });

  let [convo, setConvo] = useState([])

  useEffect(() => {
      convo = convo
    }, [convo]);


  const autoExpandTextareas = document.querySelectorAll("textarea.auto-expand");

  function addMultiEventListeners(el, s, fn) {
  s.split(" ").forEach(e => el.addEventListener(e, fn, false));
  }

  autoExpandTextareas.forEach(function(el) {
  addMultiEventListeners(el, "change keydown paste", function() {
      autoExpand(el);
  });
  });

  function autoExpand(el) {
  setTimeout(function() {
      el.style.cssText = "height: auto";
      el.style.cssText = `height: ${7 + el.scrollHeight}px`;
  }, 0);
  }

  window.onresize = function() {
  autoExpandTextareas.forEach(function(el) {
      autoExpand(el);
  });
  };

  const [docs, setDocs] = useState({
    files: null, // Initial value will be null or empty array
    username: "",
    loading : false,
    status: "",
    status_flag: false,
    error: false,
    next: false, 
    vectorStore: [],
    vsName: "",
    upload : false,
  });
  const greetings = ["hi","Hi","HI", "Hello", "hello", "Good morning"]

  const submitForm = async (e) => {
    if(greetings.includes(data.query)){
      convo.push({
          data: data.query,
          type: 0,
        });
      convo.push({
          data: "Hi Junivator, Welcome to GDC Cognitive System, How can I help you today?",
          type: 1,
      });
      setData({...data, query: "" });
    }else if(data.query){
        convo.push({
            data: data.query,
            type: 0,
          });
        setData({...data, query: "" });
        try {
            let res = await axios.get(`${apiURL}cust_llm/?prompt=${data.query}`);
            console.log("response: ", res)
            convo.push({
                data: res.data,
                type: 1,
              });
            setData({...data, query: "" });
            setScrollPosition(chatbox);
            return res.data; 
        } catch (error) {
            console.log("error: ",error);
            
            if(error){
                convo.push({
                    data: "There seems to be an issue with our compute service, please try after some time",
                    type: 1,
                });
                setData({...data, query: "" });
            }
        }
    }else{
        convo.push({
            data: data.query,
            type: 0,
          });
        convo.push({
            data: "Looks like you sent an empty prompt! Well, I cant read your mind, so please type your prompts/queries",
            type: 1,
        });
        setData({...data, query: "" });
    }
  }
  const chatbox = useRef(null)
    useEffect(()=> chatbox.current?.scrollIntoView({behavior: "smooth"}),[])
    const setScrollPosition = (element) => {
        window.scrollTo(0, 1000, {
          behavior: "smooth"
        });
      };

  const uploadDocs = async (e) => {
    let formData = new FormData();
    for (const file of docs.files) {
      formData.append("docs", file);
    }
    formData.append("username", docs.username);
    formData.append("vectorstore", docs.vsName);
    try {
        let res = await axios.post(`${apiURL}api/docs`,formData);
        console.log("response: ", res)
        setDocs({
          ...docs,
          error: false,
          loading: false,
          username: null,
          vsName: null,
          status: "Training successful!",
          status_flag : false,
          files: null,
          upload : true,
        })

        return res.data;
    } catch (error) {
        console.log(error);
    }
  }
  const fetchVectorStores = async (username) => {
    try {
      let res = await getVectorStores(username)
      console.log("response: ", res)
      setDocs({
        ...docs,
        next : 1,
        loading: false,
        vectorStore: res,
      })
      return res;
    } catch (error) {
        console.log(error);
    }
  }

  const loadDoc = async (formData) => {
    try {
      let res = await axios.get(`${apiURL}api/loaddocs`, {
        params: {
          username: docs.username,
          vectorstore: formData.name
        }
      });
      console.log("response: ", res)
      if(res && res.data){
        setDocs({
          ...docs,
          error: false,
          loading: false,
          status: "Training successful!",
          status_flag : false,
          files: null,
          vsName: "",
          upload : true,
        })
        return res.data;
      }
      return res.error
    } catch (error) {
        console.log(error);
    }
  }

  return (
    <Fragment >
      <div className="navber" style={{backgroundImage: `url(${bg2})`}}>
        <div className="subtitle" style={{color: "white", marginTop: "5vh"}}>
            GDCI LLM - Trainable
        </div>
        <div className="upload" style={docs.upload ? {display: "none"} : {}}>
          <div className="username_block" style={docs.next ? {display: "none"} : {}}>
            <div style={{fontSize: "40px", marginTop:"5rem", margin:"2rem"}}>
              Please enter the username:<br/>
            </div>
            
            <input
              placeholder="Enter your Username"
              value={docs.username}
              onChange={(e) =>
                setDocs({
                  ...docs,
                  error: false,
                  username: e.target.value,
                })
              }
              className="username"
              type="text"
            />
            <div className="train_btn">
              <Button variant="contained" endIcon={<SendIcon />} size="large" color="success"  
                onClick={(e) =>{ 
                  fetchVectorStores(docs.username)
                  setDocs({
                    ...docs,
                    loading: true,
                    // status: "Model training under way, please wait... ",
                    next : 1,
                    // status_flag: 1,
                  })
                }}>
                Next
              </Button>
            </div>
          </div>
          <div className="train_btn username_block"  style={docs.next === 1 ? {} : {display: "none"} }>
            <div style={{fontSize: "40px", marginTop:"5rem", margin:"2rem"}}>
              Please select the vector store:<br/>
            </div>
            <div className="vs_main" style={{padding: "10px"}}>
              
              {docs.vectorStore && docs.vectorStore.length > 0 ? (
                docs.vectorStore.map((item, key) => {
                  console.log("item: ",item)
                  return (
                    <Fragment>
                      <div className="vdb" onClick={(e)=>{
                        loadDoc(item)
                      }}>
                        {item.name}
                      </div>
                    </Fragment>
                  );
                })
              ) : (
                <Fragment>
                  <div className="vectorstore" >
                    No Vector Stores Found
                  </div>
                </Fragment>                  
              )}
              
            </div>
            <div className="new_vs" onClick={(e)=>{
              setDocs({
                ...docs,
                loading: false,
                // status: "Model training under way, please wait... ",
                next: 2,
              })
            }}>
              <AddCircleIcon fontSize="large" style={{height:'4vh', width:'4vh', margin: 'auto',color: 'rgba(0, 0, 0, 0.637)'}}/>
              
            </div>
            {/* <div className="train_btn">
              <Button variant="contained" endIcon={<SendIcon />} size="large" color="success"  onClick={(e) =>{ 
                  setDocs({
                    ...docs,
                    loading: true,
                    status: "Model training under way, please wait... ",
                    status_flag: 1,
                  })
                  uploadDocs(e)
                } }>
                Load Vector Store
              </Button>
            </div> */}

          </div>

          <div className="train_btn" style={docs.next === 2 ? {} : {display: "none"} }>
            <div style={{fontSize: "40px", marginTop:"5rem", margin:"2rem"}}>
              Please enter the VectorStore Name:<br/>
            </div>
            
            <input
              placeholder="Enter VectorStore Name"
              value={docs.vsName}
              onChange={(e) =>
                setDocs({
                  ...docs,
                  error: false,
                  vsName: e.target.value,
                })
              }
              className="username"
              type="text"
            />
            <div style={{fontSize: "20px", marginTop:"5rem", margin:"2rem"}}>
              Please Upload the Files:<br/>
            </div>
            <div style={{padding: "10px", marginLeft: "80px"}}>
              <input
                onChange={(e) =>
                  setDocs({
                    ...docs,
                    error: false,
                    files: [...e.target.files],
                  })
                }
                type="file"
                accept=".pdf"
                className="px-4 py-2 border focus:outline-none file_field"
                style={{marginBottom: "20px", height: "3vh"}}
                id="image"
                multiple
              />

            </div>
            <div className="train_btn">
              <Button variant="contained" endIcon={<SendIcon />} size="large" color="success"  onClick={(e) =>{ 
                  setDocs({
                    ...docs,
                    loading: true,
                    status: "Model training under way, please wait... ",
                    status_flag: 1,
                  })
                  uploadDocs(e)
                } }>
                Train
              </Button>
            </div>
            
          </div>
          <Box sx={{ width: '80%' }} className="loader" style={docs.loading  ? {display: "block"}: {display: "none"}}>
            <LinearProgress />
            <div style={docs.status_flag ? { padding: "40px", fontSize:"40px"} : {display: "none"}}>
              {docs.status}
            </div>
          </Box>
         
        </div>

        <ScrollToBottom className ={ ` ${docs.upload?  'chatbox' : 'chatbox1'}` } >
          <ScrollToBottom >
              {convo.map(msg => (  
                  <div className="msgs">
                      <span className= "msg_span" style={msg.type ? {backgroundColor: "#2c6a00"} : { backgroundColor : "#303030"}}><pre style={{textWrap: "wrap"}}>{msg.data}</pre></span>
                  </div>
              ))}
          </ScrollToBottom>         
          <textarea 
              rows='1' className='auto-expand input' id="textarea1" placeholder="Enter some text..."
              onChange={(e) => {
                  setData({...data, query: e.target.value });
              }}
              value={data.query}
              type="text" 
          ></textarea> 
          <div className="submit_2">
              <Button variant="contained" endIcon={<SendIcon />} color="success" onClick={(e) => submitForm(e)}>
                  Send
              </Button>
          </div>

        </ScrollToBottom>
      </div>
    </Fragment>
  );
};



const Untrained = (props) => {
    const [data, dispatch] = useReducer(layoutReducer, layoutState);
    return (
        <Fragment>
            <LayoutContext.Provider value={{ data, dispatch }}>
                <Layout children={<UntrainedComponent />} />
            </LayoutContext.Provider>
        </Fragment>
    );
}


export default Untrained;
