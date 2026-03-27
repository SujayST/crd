import { Fragment, useEffect, useReducer, useRef, useState } from "react";
import { layoutReducer, layoutState } from "../layout/layoutContext";
import Layout, { LayoutContext } from "../layout";
import Button from '@mui/material/Fab';
import IconButton from '@mui/material/IconButton';
import SendIcon from '@mui/icons-material/Send';
import DeleteIcon from '@mui/icons-material/Delete';
import ThumbUpAltIcon from '@mui/icons-material/ThumbUpAlt';
import ThumbDownAltIcon from '@mui/icons-material/ThumbDownAlt';
import "./style.css";
import ScrollToBottom from 'react-scroll-to-bottom';
import axios from "axios";

const apiURL = process.env.REACT_APP_API_URL;



const ConfigConverterComponent = () => {
    const [data, setData] = useState({
        query: "",
        loading: false,
    });

    let [convo, setConvo] = useState([])

    let [res, setRes] = useState([])

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
    const greetings = ["hi","Hi", "Hello", "hello", "Good morning"]
    const closure = ["close", "Close", "thankyou", "Thankyou", "Thank you", "thank you", "bye", "Bye"]

    const submitForm = async (e) => {
//        setData({...data, loading: !data.loading})
        if(greetings.includes(data.query)){
            convo.push({
                data: data.query,
                type: 0,
              });
            convo.push({
                data: "Hi Junivator, Welcome to GDC Cognitive System, How can I help you today?",
                type: 1,
            });
            setRes("Hi Junivator, Welcome to GDC Cognitive System, How can I help you today?")
            // setData({...data, query: "" });
        }else if(closure.includes(data.query)){
            convo.push({
                data: data.query,
                type: 0,
              });
            convo.push({
                data: "Im glad I could be of use for you today, please provide your valuable feedback... ",
                type: 1,
            });
            setRes("Im glad I could be of use for you today, please provide your valuable feedback... ")
            // setData({...data, query: "" });
            setTimeout(() => {
                window.location.href = 'https://forms.office.com/pages/responsepage.aspx?id=PIunvttMMEGFSh0ZMjLl9DULU0uAXTFFvCeQXaFxhExUQkZJSDlQSkZMT1hBNEYzSkxZMjc3WlZKUS4u';
            }, 2000);

        }else if(data.query){
            convo.push({
                data: data.query,
                type: 0,
              });
            // setData({...data, query: "" });
            setData({...data, loading: !data.loading})

            try {
                let res = await axios.get(`${apiURL}configconverter/?prompt=${data.query}`);
                console.log("response: ", res)
                setData({...data, loading: !data.loading})
                setRes(res.data)
                convo.push({
                    data: res.data,
                    type: 1,
                  });
                // setData({...data, query: "" });
                setScrollPosition(chatbox);
                return res.data;
            } catch (error) {
                console.log("error: ",error);

                if(error){
                    setRes("There seems to be an issue with our compute service, please try after some time")
                    convo.push({
                        data: "There seems to be an issue with our compute service, please try after some time",
                        type: 1,
                    });
                    // setData({...data, query: "" });
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
            // setData({...data, query: "" });
        }
    }
    const submitup = async (e) => {
        convo.push({
                    data: "Great! I'm glad the response was helpful.",
                    type: 2,
                  });
                // setData({...data, query: "" });
                setScrollPosition(chatbox);
    }
    const submitdown = async (e) => {
        try {
                let res = await axios.get(`${apiURL}check_response/?response=${"no"}`);
                console.log("response: ", res)
                convo.push({
                    data: res.data,
                    type: 2,
                  });
                // setData({...data, query: "" });
                setScrollPosition(chatbox);
                return res.data;
            } catch (error) {
                console.log("error: ",error);

                if(error){
                    convo.push({
                        data: "Thank you for the feedback, i will try to do better the next time!",
                        type: 2,
                    });
                    // setData({...data, query: "" });
                }
            }
    }


    const chatbox = useRef(null)
    useEffect(()=> chatbox.current?.scrollIntoView({behavior: "smooth"}),[])
    const setScrollPosition = (element) => {
        window.scrollTo(0, 1000, {
          behavior: "smooth"
        });
      };

    return (
      <Fragment >
        <div className="navber">
         <div className="subtitle">
            Cisco to JUNOS Config Converter
         </div>
         <div className="chatbox" >

            {/* <ScrollToBottom >
                {convo.map(msg => (
                    <Fragment>
                        <div style={{display: "flex", flexDirection: "column"}}>
                            <div className="msgs">
                                <span className= "msg_span" style={msg.type===1 ? {backgroundColor: "#2c6a00"} : (msg.type===2 ? { backgroundColor : "#30303050"}:{ backgroundColor : "#303030"})}><pre style={{textWrap: "wrap"}}>{msg.data}</pre></span>
                            </div>
                            <div style={(msg.type===1) ?{marginTop: "-15px"}:{display: "none"}}>
                                <IconButton aria-label="thumbs up" onClick={(e) => submitup(e)}>
                                    <ThumbUpAltIcon />
                                </IconButton>
                                <IconButton aria-label="thumbs down" onClick={(e) => submitdown(e)}>
                                    <ThumbDownAltIcon />
                                </IconButton>
                            </div>
                        </div>

                    </Fragment>

                ))}
            </ScrollToBottom> */}
            {/* <div style={{display: "flex", flexDirection: "row"}}> */}
                <div>
                    <textarea
                        rows='30' className='auto-expand ' id="textarea1" placeholder="Enter the cisco prompt that needs to be converted ..."
                        onChange={(e) => {
                            setData({...data, query: e.target.value });
                        }}
                        value={data.query}
                        type="text"
                    ></textarea>
                </div>
                <div className='auto-expand '>
                    {data.loading ? (
                        <div style={{display: 'flex', height: '5vw', justifyContent: 'center', }}>
                            <svg
                            className="w-12 h-12 animate-spin text-gray-600"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                            xmlns="http://www.w3.org/2000/svg"
                            >
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth="2"
                                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                            ></path>
                            </svg>
                        </div>
                    ): (<div>{res}</div>)}
                    
                </div>
            {/* </div> */}
            <div className="submit">
                <Button variant="contained" size="large" style={{height:'7vw', width: '7vw'}} endIcon={<SendIcon />} color="success" onClick={(e) => submitForm(e)}>
                    Convert
                </Button>
            </div>
         </div>
        </div>
      </Fragment>
    );
  };



const ConfigConverter = (props) => {
    const [data, dispatch] = useReducer(layoutReducer, layoutState);
    return (
        <Fragment>
            <LayoutContext.Provider value={{ data, dispatch }}>
                <Layout children={<ConfigConverterComponent />} />
            </LayoutContext.Provider>
        </Fragment>
    );
}


export default ConfigConverter;
