import React, { Fragment, useReducer, useState } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import * as XLSX from "xlsx";
import jsPDF from "jspdf";
import { Button, TextField, Typography, Paper, CircularProgress, FormControl, InputLabel, Select, MenuItem, Box, FormGroup, FormControlLabel, Checkbox } from '@mui/material';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import { styled } from '@mui/system';
import { layoutReducer, layoutState } from "../layout/layoutContext";
import Layout, { LayoutContext } from "../layout";

const apiURL = process.env.REACT_APP_API_URL;

const downloadObjectAsExcel = (data, filename) => {
  const worksheet = XLSX.utils.json_to_sheet(data);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, "Questions");
  XLSX.writeFile(workbook, `${filename}.xlsx`);
};

const theme = createTheme({
  palette: { primary: { main: '#1976d2' }, secondary: { main: '#dc004e' } },
});

const StyledPaper = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(4), margin: theme.spacing(4), flex: 1, borderRadius: theme.spacing(2),
  boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.1)', display: 'flex', flexDirection: 'column',
  alignItems: 'center', background: '#f9f9f9'
}));

const StyledButton = styled(Button)(({ theme }) => ({
  marginTop: theme.spacing(3), padding: theme.spacing(1.5, 6),
  borderRadius: theme.spacing(1), fontSize: '1.1rem',
}));

const CrdGeneratorComponent = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [username, setUsername] = useState('');
  const [projectName, setProjectName] = useState('');
  const [projectId, setProjectId] = useState('');
  const [domain, setDomain] = useState('');
  const [subDomain, setSubDomain] = useState('');
  const [files, setFiles] = useState(null);
  
  const [apiResponse, setApiResponse] = useState(null);
  const [selectedTopics, setSelectedTopics] = useState({});
  const [selectedQuestions, setSelectedQuestions] = useState({});
  const [customQuestions, setCustomQuestions] = useState({});
  const [userDefinedTopics, setUserDefinedTopics] = useState([]);
  const [newCustomTopicName, setNewCustomTopicName] = useState('');
  const [newCustomQuestion, setNewCustomQuestion] = useState({});
  const [showAddTopicInput, setShowAddTopicInput] = useState(false);
  
  const [iterationData, setIterationData] = useState([]);
  const [uploadedAnswersFile, setUploadedAnswersFile] = useState(null);
  const [finalCRD, setFinalCRD] = useState(null);

  const parseExcelFile = async (file) => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const data = new Uint8Array(e.target.result);
          const workbook = XLSX.read(data, { type: 'array' });
          const sheetName = workbook.SheetNames[0];
          const worksheet = workbook.Sheets[sheetName];
          
          const json = XLSX.utils.sheet_to_json(worksheet, { defval: "" });

          const parsedQuestions = {};
          const parsedAnswers = {};
          
          let lastSeenTopic = "Uncategorized";

          json.forEach(row => {
            let rowTopic = "";
            let question = "";
            let answer = "";

            Object.keys(row).forEach(key => {
              const normalizedKey = key.trim().toLowerCase();
              if (normalizedKey.includes("topic")) rowTopic = row[key];
              if (normalizedKey.includes("question")) question = row[key];
              if (normalizedKey.includes("answer") || normalizedKey.includes("vil response")) {
                  answer = row[key];
              }
            });

            if (rowTopic && rowTopic.toString().trim() !== "") {
                lastSeenTopic = rowTopic.toString().trim();
            }
            const activeTopic = lastSeenTopic;

            if (question && question.toString().trim() !== "") {
              const cleanQuestion = question.toString().trim();
              
              if (!parsedQuestions[activeTopic]) {
                parsedQuestions[activeTopic] = [];
              }
              if (!parsedQuestions[activeTopic].includes(cleanQuestion)) {
                parsedQuestions[activeTopic].push(cleanQuestion);
              }
              
              parsedAnswers[cleanQuestion] = answer.toString().trim();
            }
          });

          resolve({ questions: parsedQuestions, answers: parsedAnswers });
        } catch (error) {
          console.error("Error during excel parsing:", error);
          reject(error);
        }
      };
      reader.readAsArrayBuffer(file);
    });
  };

  const handleGenerateQuestions = async () => {
    setLoading(true); setError('');
    const formData = new FormData();
    formData.append("project_id", projectId); 
    formData.append("project_name", projectName);
    formData.append("domain", domain); 
    formData.append("segment", subDomain); 
    formData.append("username", username);
    
    if (uploadedAnswersFile) {
      formData.append("files", uploadedAnswersFile); 
    } else if (files && files.length > 0) {
      for (let i = 0; i < files.length; i++) formData.append("files", files[i]);
    }
    if (iterationData.length > 0) formData.append("previous_iterations", JSON.stringify(iterationData));

    try {
      const endpoint = uploadedAnswersFile ? '/api/ingest/customer-excel/' : '/api/ingest/crd-docs/';
      const response = await axios.post(`${apiURL}${endpoint}`, formData);
      if (response && response.data ) {
        console.log("API Response:", response.data);
        if (response.data.questions) {
          setApiResponse(response.data.questions); 
        } else{
        setApiResponse(response.data); 
        }
        setStep(3);
      } else setError('API returned empty data.');
    } catch (apiError) {
      setError('Failed to fetch suggested topics and questions.');
    } finally { setLoading(false); }
  };

  const handleTopicToggle = (topicName) => setSelectedTopics(prev => ({ ...prev, [topicName]: !prev[topicName] }));
  const handleQuestionToggle = (topicName, question) => {
    setSelectedQuestions(prev => ({ ...prev, [topicName]: { ...(prev[topicName] || {}), [question]: !prev[topicName]?.[question] } }));
  };

  const handleAddCustomQuestion = (topicName) => {
    const questionToAdd = newCustomQuestion[topicName]?.trim();
    if (!questionToAdd) return;
    setCustomQuestions(prev => ({ ...prev, [topicName]: [...(prev[topicName] || []), questionToAdd] }));
    setSelectedQuestions(prev => ({ ...prev, [topicName]: { ...(prev[topicName] || {}), [questionToAdd]: true } }));
    setNewCustomQuestion(prev => ({ ...prev, [topicName]: '' }));
  };
  const addCustomQuestion = async (question, topicName) => {
    setLoading(true); setError('');
    const formData = new FormData();
    formData.append("Question", question); 
    formData.append("topicName", topicName);

    try {
      const endpoint = '/api/ingest/sme-questions/';
      const response = await axios.post(`${apiURL}${endpoint}`, formData);
      if (response && response.data ) {
        console.log("API Response:", response.data);
        if (response.data.questions) {
          setApiResponse(response.data.questions); 
        } else{
        setApiResponse(response.data); 
        }
        setStep(3);
      } else setError('API returned empty data.');
    } catch (apiError) {
      setError('Failed to fetch suggested topics and questions.');
    } finally { setLoading(false); }
  }

  const handleAddCustomTopic = () => {
    const topicName = newCustomTopicName.trim();
    if (!topicName) return;
    setUserDefinedTopics(prev => [...prev, { name: topicName, questions: [] }]);
    setSelectedTopics(prev => ({ ...prev, [topicName]: true }));
    setNewCustomTopicName(''); setShowAddTopicInput(false);
  };

  const handleDownloadExcel = async () => {
    let topicList = apiResponse?.topics ? Object.entries(apiResponse.topics).map(([name, data]) => ({ name, questions: data.generated_questions || data.followup_questions || [] })) : [];
    const selectedQuestionsForDownload = {};
    
    // 1. Build the Excel Data
    Object.keys(selectedTopics).filter(topic => selectedTopics[topic]).forEach(topicName => {
      const questions = [];
      
      const apiTopic = topicList.find(t => t.name === topicName);
      if (apiTopic) {
        questions.push(...apiTopic.questions.filter(q => selectedQuestions[topicName]?.[q]));
      }
      
      if (customQuestions[topicName]) {
        questions.push(...customQuestions[topicName].filter(q => selectedQuestions[topicName]?.[q]));
      }
      
      if (questions.length > 0) {
        selectedQuestionsForDownload[topicName] = questions;
      }
    });

    if (Object.keys(selectedQuestionsForDownload).length === 0) {
      return setError("Please select at least one question to download.");
    }
    setError('');

    // --- NEW: Collect and submit custom questions ---
    const customQuestionsPayload = {};
    
    Object.keys(customQuestions).forEach(topicName => {
      // Only grab custom questions that the user actually kept selected
      const approvedCustomQs = customQuestions[topicName].filter(q => selectedQuestions[topicName]?.[q]);
      
      if (approvedCustomQs.length > 0) {
        // Format topic name to match your JSON example (lowercase, replace spaces with underscores)
        const formattedTopicName = topicName.toLowerCase().replace(/\s+/g, '_');
        customQuestionsPayload[formattedTopicName] = {
          approved_questions: approvedCustomQs
        };
      }
    });

    // If there are any custom questions, fire off the API call
    if (Object.keys(customQuestionsPayload).length > 0) {
      const payload = {
        domain: domain,        // Maps to "sp", "Networking", etc.
        segment: subDomain,    // Maps to "routing", "switching", etc.
        topics: customQuestionsPayload
      };
      setLoading(true);
      try {
        // NOTE: Update this endpoint to match your actual backend route
        await axios.post(`${apiURL}/api/ingest/sme-questions/`, payload);
        console.log("Successfully submitted custom questions:", payload);
        setLoading(false);
      } catch (err) {
        setLoading(false);
        console.error("Failed to submit custom questions to the backend:", err);
        // We catch the error but don't block the download, so the user flow isn't interrupted
      }
    }
    // ------------------------------------------------

    // 2. Proceed with downloading the Excel file
    const excelData = Object.entries(selectedQuestionsForDownload).flatMap(([topic, questions]) => 
      questions.map(question => ({ Topic: topic, Question: question, Answer: '' }))
    );

    downloadObjectAsExcel(excelData, 'Customer_Questions');
    setIterationData(prev => [...prev, { questions: selectedQuestionsForDownload, answers: null }]);
    setApiResponse(null); 
    setSelectedTopics({}); 
    setSelectedQuestions({}); 
    setUploadedAnswersFile(null); 
    setStep(4);
  };

  // const handleDownloadExcel = () => {
  //   let topicList = apiResponse?.topics ? Object.entries(apiResponse.topics).map(([name, data]) => ({ name, questions: data.generated_questions || data.followup_questions || [] })) : [];
  //   const selectedQuestionsForDownload = {};
    
  //   Object.keys(selectedTopics).filter(topic => selectedTopics[topic]).forEach(topicName => {
  //     const questions = [];
      
  //     const apiTopic = topicList.find(t => t.name === topicName);
  //     if (apiTopic) {
  //       questions.push(...apiTopic.questions.filter(q => selectedQuestions[topicName]?.[q]));
  //     }
      
  //     if (customQuestions[topicName]) {
  //       questions.push(...customQuestions[topicName].filter(q => selectedQuestions[topicName]?.[q]));
  //     }
      
  //     if (questions.length > 0) {
  //       selectedQuestionsForDownload[topicName] = questions;
  //     }
  //   });

  //   if (Object.keys(selectedQuestionsForDownload).length === 0) return setError("Please select at least one question to download.");

  //   setError('');
  //   const excelData = Object.entries(selectedQuestionsForDownload).flatMap(([topic, questions]) => 
  //     questions.map(question => ({ Topic: topic, Question: question, Answer: '' }))
  //   );

  //   downloadObjectAsExcel(excelData, 'Customer_Questions');
  //   setIterationData(prev => [...prev, { questions: selectedQuestionsForDownload, answers: null }]);
  //   setApiResponse(null); setSelectedTopics({}); setSelectedQuestions({}); setUploadedAnswersFile(null); setStep(4);
  // };

  const handleUploadAnswers = async () => {
    if (!uploadedAnswersFile) return setError("Please upload the answered Excel file.");
    setLoading(true);
    try {
      const { questions, answers } = await parseExcelFile(uploadedAnswersFile);
      setIterationData(prev => {
          const newIteration = { questions, answers };
          return prev.length > 0 ? [...prev.slice(0, prev.length - 1), newIteration] : [newIteration];
      });
      setStep(5);
    } catch (e) { setError("Failed to parse the uploaded file."); } finally { setLoading(false); }
  };

  const handleGenerateFinalCRD = async () => {
    setLoading(true);
    try {
      const finalIteration = iterationData[iterationData.length - 1];
      if (!finalIteration || !finalIteration.questions) {
        setError("No data available to generate CRD.");
        setLoading(false);
        return;
      }

      const doc = new jsPDF();
      let yOffset = 20;

      doc.setFontSize(22);
      doc.setFont("helvetica", "bold");
      doc.text("Customer Requirements Document", 14, yOffset);
      yOffset += 10;
      
      doc.setFontSize(12);
      doc.setFont("helvetica", "normal");
      doc.text(`Project Name: ${projectName || 'N/A'}`, 14, yOffset);
      yOffset += 7;
      doc.text(`Domain: ${domain || 'N/A'} - ${subDomain || 'N/A'}`, 14, yOffset);
      yOffset += 15;

      Object.entries(finalIteration.questions).forEach(([topic, questions]) => {
        if (yOffset > 270) {
          doc.addPage();
          yOffset = 20;
        }

        doc.setFontSize(16);
        doc.setFont("helvetica", "bold");
        doc.setTextColor(25, 118, 210);
        doc.text(topic.replace('-', ' ').toUpperCase(), 14, yOffset);
        yOffset += 10;
        
        doc.setTextColor(0, 0, 0);
        doc.setFontSize(11);

        questions.forEach((q) => {
          const answer = finalIteration.answers[q] || 'No answer provided.';
          
          const splitQuestion = doc.splitTextToSize(`Q: ${q}`, 180);
          const splitAnswer = doc.splitTextToSize(`A: ${answer}`, 180);
          
          const totalLineHeight = (splitQuestion.length * 6) + (splitAnswer.length * 6) + 5;

          if (yOffset + totalLineHeight > 280) {
            doc.addPage();
            yOffset = 20;
          }
          
          doc.setFont("helvetica", "bold");
          doc.text(splitQuestion, 14, yOffset);
          yOffset += splitQuestion.length * 6;
          
          doc.setFont("helvetica", "normal");
          doc.text(splitAnswer, 14, yOffset);
          yOffset += splitAnswer.length * 6 + 6; 
        });
        
        yOffset += 8; 
      });

      const safeProjectName = (projectName || "Project").replace(/\s+/g, "_");
      doc.save(`${safeProjectName}_Final_CRD.pdf`);

      setFinalCRD(`Final CRD Document successfully generated and downloaded as "${safeProjectName}_Final_CRD.pdf".`);
      setStep(6);
    } catch (e) { 
      console.error(e);
      setError("Failed to generate the final CRD PDF."); 
    } finally { 
      setLoading(false); 
    }
  };

  const handleStartOver = () => {
    setUsername(''); setProjectName(''); setProjectId(''); setDomain(''); setSubDomain(''); setFiles(null);
    setApiResponse(null); setSelectedTopics({}); setSelectedQuestions({}); setCustomQuestions({}); 
    setUserDefinedTopics([]); setIterationData([]); setUploadedAnswersFile(null); setStep(1); setLoading(false); setError('');
  };

  const renderStep1 = () => (
    <div className="flex flex-col gap-8 pb-5 w-full max-w-xl">
      <TextField fullWidth label="Username" value={username} onChange={(e) => setUsername(e.target.value)} />
      <TextField fullWidth label="Project Name" value={projectName} onChange={(e) => setProjectName(e.target.value)} />
      <TextField fullWidth label="Project ID" value={projectId} onChange={(e) => setProjectId(e.target.value)} />
    </div>
  );

  const renderStep2 = () => (
    <div className="flex flex-col gap-8 pb-5 w-full max-w-xl">
      <FormControl fullWidth>
        <InputLabel>Domain</InputLabel>
        <Select value={domain} label="Domain" onChange={(e) => setDomain(e.target.value)}>
          <MenuItem value="Networking">Networking</MenuItem><MenuItem value="Security">Security</MenuItem>
          <MenuItem value="Cloud">Cloud</MenuItem><MenuItem value="sp">Service Provider</MenuItem>
        </Select>
      </FormControl>
      <FormControl fullWidth>
        <InputLabel>Segment</InputLabel>
        <Select value={subDomain} label="Sub-Domain" onChange={(e) => setSubDomain(e.target.value)}>
          <MenuItem value="routing">Routing</MenuItem><MenuItem value="switching">Switching</MenuItem>
          <MenuItem value="wireless">Wireless</MenuItem>
        </Select>
      </FormControl>
      <Button variant="outlined" component="label" fullWidth startIcon={<UploadFileIcon />} style={{ padding: '15.5px 14px', justifyContent: 'center', backgroundColor: '#509b28', color: 'white' }}>
        {files ? `${files.length} file(s) selected` : 'Upload Customer Interaction Documents'}
        <input type="file" hidden multiple onChange={(e) => setFiles(e.target.files)} />
      </Button>
    </div>
  );

  const renderStep3 = () => {
    const allTopics = apiResponse?.topics ? Object.entries(apiResponse.topics).map(([name, data]) => ({ name, questions: data.generated_questions || data.followup_questions || [] })) : [];
    return (
      <div className="flex flex-col gap-4 pb-5 w-full max-w-3xl" style={{ overflowY: 'auto' }}>
        <Typography variant="h5" gutterBottom>Select Topics and Questions</Typography>
        {allTopics.map((topic, index) => (
          <Box key={topic.name || index} sx={{ border: '1px solid #ddd', borderRadius: '8px', p: 2, mb: 2, background: '#fff' }}>
            <FormControlLabel control={<Checkbox checked={!!selectedTopics[topic.name]} onChange={() => handleTopicToggle(topic.name)}/>} label={<Typography variant="h6" sx={{ textTransform: 'capitalize' }}>{topic.name.replace('-', ' ')}</Typography>} />
            {selectedTopics[topic.name] && (
              <Box sx={{ pl: 4, mt: 1 }}>
                <Typography variant="subtitle1" gutterBottom>Questions</Typography>
                <FormGroup>
                  {topic.questions && topic.questions.map((question) => (<FormControlLabel key={question} control={<Checkbox checked={!!selectedQuestions[topic.name]?.[question]} onChange={() => handleQuestionToggle(topic.name, question)}/>} label={question} />))}
                  {customQuestions[topic.name]?.map((question) => (<FormControlLabel key={question} control={<Checkbox checked onChange={() => handleQuestionToggle(topic.name, question)} />} label={<i>{question} (custom)</i>} />))}
                </FormGroup>
                <Box sx={{ display: 'flex', alignItems: 'center', mt: 2, gap: 2 }}>
                  <TextField fullWidth variant="standard" label="Add a custom question" value={newCustomQuestion[topic.name] || ''} 
                    onChange={(e) => {
                      setNewCustomQuestion(prev => ({ ...prev, [topic.name]: e.target.value }))
                    }} 
                    onKeyPress={(e) => e.key === 'Enter' && handleAddCustomQuestion(topic.name)} 
                  />
                  <Button variant="contained" size="small" onClick={() => handleAddCustomQuestion(topic.name)}>Add</Button>
                </Box>
              </Box>
            )}
          </Box>
        ))}
        {userDefinedTopics.map((topic, index) => (
             <Box key={`custom-${index}`} sx={{ border: '1px solid #ddd', borderRadius: '8px', p: 2, mb: 2, background: '#fff' }}>
                <FormControlLabel control={<Checkbox checked={!!selectedTopics[topic.name]} onChange={() => handleTopicToggle(topic.name)}/>} label={<Typography variant="h6">{topic.name} (Custom Topic)</Typography>} />
                 {selectedTopics[topic.name] && (
                     <Box sx={{ pl: 4, mt: 1 }}>
                         <Typography variant="subtitle1">Add questions below</Typography>
                          <Box sx={{ display: 'flex', alignItems: 'center', mt: 2, gap: 2 }}>
                            <TextField fullWidth variant="standard" label="Add a custom question" value={newCustomQuestion[topic.name] || ''} onChange={(e) => setNewCustomQuestion(prev => ({ ...prev, [topic.name]: e.target.value }))} onKeyPress={(e) => e.key === 'Enter' && handleAddCustomQuestion(topic.name)} />
                            <Button variant="contained" size="small" onClick={() => handleAddCustomQuestion(topic.name)}>Add</Button>
                        </Box>
                         <FormGroup>{customQuestions[topic.name]?.map((question) => (<FormControlLabel key={question} control={<Checkbox checked onChange={() => handleQuestionToggle(topic.name, question)} />} label={question} />))}</FormGroup>
                     </Box>
                 )}
             </Box>
        ))}
        {!showAddTopicInput ? (
          <Button variant="outlined" onClick={() => setShowAddTopicInput(true)} style={{ marginTop: '16px', alignSelf: 'center' }}>Add New Topic</Button>
        ) : (
          <Box sx={{ border: '1px dashed #ccc', borderRadius: '8px', p: 2, mt: 2, background: '#f0f0f0' }}>
            <Typography variant="h6" gutterBottom>Add New Topic</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, gap: 2 }}>
              <TextField fullWidth variant="standard" label="New Topic Name" value={newCustomTopicName} onChange={(e) => setNewCustomTopicName(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && handleAddCustomTopic()} />
              <Button variant="contained" size="small" onClick={handleAddCustomTopic}>Add Topic</Button>
            </Box>
          </Box>
        )}
      </div>
    );
  };

  const renderStep4 = () => (
    <div className="flex flex-col gap-8 pb-5 w-full max-w-xl text-center">
      <Typography variant="h5">Awaiting Customer Answers</Typography>
      <Button variant="outlined" component="label" fullWidth startIcon={<UploadFileIcon />} style={{ padding: '15.5px 14px', justifyContent: 'center' }}>
        {uploadedAnswersFile ? uploadedAnswersFile.name : 'Upload Answered File'}
        <input type="file" hidden accept=".xlsx, .xls" onChange={ async(e) => {
            const file = e.target.files[0];
            if (file) { setUploadedAnswersFile(file); e.target.value = null; }
        }} />
      </Button>
    </div>
  );

  const renderStep5 = () => (
    <div className="flex flex-col gap-4 pb-5 w-full max-w-3xl" >
      <Typography variant="h5">Review Answers</Typography>
      <Box style={{ maxHeight: '40vh', overflowY: 'auto', padding: '1rem', border: '1px solid #ccc', borderRadius: '8px', background: '#fff' }}>
        {iterationData.map((iter, index) => (
          <div key={index} style={{ marginBottom: '2rem' }}>
            <Typography variant="h6" sx={{ mb: 1, borderBottom: '1px solid #eee', paddingBottom: '8px' }}>Iteration {index + 1}</Typography>
            {Object.entries(iter.questions || {}).map(([topic, questions]) => (
              <Box key={topic} sx={{ mb: 3, pl: 2, borderLeft: '3px solid #1976d2', background: '#fafafa', padding: '10px' }}>
                <Typography variant="subtitle1" style={{ fontWeight: 'bold', textTransform: 'uppercase', color: '#1976d2' }}>
                  {topic?.replace('-', ' ')}
                </Typography>
                <ul style={{ listStyleType: 'none', paddingLeft: '0', marginTop: '10px' }}>
                  {Array.isArray(questions) && questions.map(q => (
                    <li key={q} style={{ marginBottom: '16px' }}>
                      <div style={{ fontWeight: '500', marginBottom: '4px' }}>Q: {q}</div>
                      <div style={{ color: '#007bff', background: '#eef6ff', padding: '8px', borderRadius: '4px' }}>
                        A: {iter?.answers?.[q] || 'No answer provided.'}
                      </div>
                    </li>
                  ))}
                </ul>
             </Box>
            ))}
          </div>
        ))}
      </Box>
    </div>
  );

  const renderStep6 = () => (
    <div className="flex flex-col gap-8 pb-5 w-full max-w-xl text-center">
      <Typography variant="h4" color="primary">CRD Generation Complete!</Typography>
      <Box sx={{ p: 2, border: '1px solid #ddd', borderRadius: '4px', background: '#f0f0f0', whiteSpace: 'pre-wrap', textAlign: 'left' }}>{finalCRD}</Box>
    </div>
  );

  return (
    <ThemeProvider theme={theme}>
      <StyledPaper>
        <div className="font-bold text-5xl p-4 mb-4">CRD Generator</div>
        {step === 1 && renderStep1()}{step === 2 && renderStep2()}{step === 3 && renderStep3()}{step === 4 && renderStep4()}{step === 5 && renderStep5()}{step === 6 && renderStep6()}
        <div style={{ display: 'flex', gap: '16px', marginTop: 'auto', justifyContent: 'space-between', alignItems: 'center', width: '100%', maxWidth: '600px' }}>
          {step > 1 && <StyledButton variant="outlined" onClick={() => setStep(step - 1)}>Back</StyledButton>}
          {step === 1 && <StyledButton variant="contained" color="primary" onClick={() => setStep(2)}>Next</StyledButton>}
          {step === 2 && <StyledButton variant="contained" color="primary" onClick={handleGenerateQuestions} disabled={loading}>{loading ? <CircularProgress size={24} /> : 'Generate Questions'}</StyledButton>}
          {step === 3 && <StyledButton variant="contained" color="primary" onClick={handleDownloadExcel}>Download Questions</StyledButton>}
          {step === 4 && <StyledButton variant="contained" color="primary" onClick={handleUploadAnswers} disabled={!uploadedAnswersFile || loading}>{loading ? <CircularProgress size={24} /> : 'Upload & Review'}</StyledButton>}
          {step === 5 && (<><StyledButton variant="outlined" onClick={handleGenerateQuestions} disabled={loading}>Generate More Questions</StyledButton><StyledButton variant="contained" color="primary" onClick={handleGenerateFinalCRD} disabled={loading}>Generate Final CRD</StyledButton></>)}
          {step === 6 && <StyledButton variant="contained" color="primary" onClick={handleStartOver}>Start Over</StyledButton>}
        </div>
        {error && <Typography color="error" style={{ marginTop: '20px' }}>{error}</Typography>}
      </StyledPaper>
    </ThemeProvider>
  );
};

const CrdGenerator = () => {
  const [data, dispatch] = useReducer(layoutReducer, layoutState);
  return (
    <Fragment>
      <div className="h-screen flex flex-col bg-gray">
        <LayoutContext.Provider value={{ data, dispatch }}><Layout children={<CrdGeneratorComponent />} /></LayoutContext.Provider>
      </div>
    </Fragment>
  );
};

export default CrdGenerator;